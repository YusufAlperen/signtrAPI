"""
İşaret Dili → Türkçe Cümle  |  FastAPI WebSocket Sunucusu  [Android uyumlu]
=============================================================================
Bağlantı: ws://<IP>:8000/ws

  İstemciden gelen:
    • Ham base64 JPEG string  (Android prefix göndermez)
    • "RESET"                 → cümleyi sıfırla

  Sunucudan giden (JSON):
    { "type": "word",     "text": "gitmek" }
    { "type": "sentence", "text": "Ben okula gidiyorum." }
    { "type": "reset",    "text": "" }
    { "type": "error",    "text": "açıklama" }
"""

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from tensorflow.keras.models import load_model
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import base64
import json
import warnings

from nlp import NLPProcessor

warnings.filterwarnings('ignore')

# ──────────────────────────────────────────────────────────────────────────────
# YAPILANDIRMA
# ──────────────────────────────────────────────────────────────────────────────
MODEL_YOLU = 'model/en_iyi_model.keras'
LABEL_YOLU = 'model/labels.txt'
POSE_TASK  = 'Landmarks/pose_landmarker.task'
HAND_TASK  = 'Landmarks/hand_landmarker.task'

GUVEN_ESIGI     = 0.70
MIN_SEKANS_KARE = 5
MAX_SEKANS_KARE = 40
BOS_KARE_ESIGI  = 3
HEDEF_KARE      = 30

# ──────────────────────────────────────────────────────────────────────────────
# MODEL & MEDIAPIPE YÜKLEMESİ
# ──────────────────────────────────────────────────────────────────────────────
print("⏳ Modeller yükleniyor, lütfen bekleyin...")

model = load_model(MODEL_YOLU)

with open(LABEL_YOLU, 'r', encoding='utf-8') as f:
    KELIMELER = [s.strip() for s in f.readlines()]

BaseOptions       = mp.tasks.BaseOptions
VisionRunningMode = mp.tasks.vision.RunningMode

pose_det = vision.PoseLandmarker.create_from_options(
    vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=POSE_TASK),
        running_mode=VisionRunningMode.IMAGE,
    )
)
hand_det = vision.HandLandmarker.create_from_options(
    vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=HAND_TASK),
        running_mode=VisionRunningMode.IMAGE,
        num_hands=2,
    )
)

nlp = NLPProcessor()
print("✅ Modeller yüklendi.")

# ──────────────────────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR  (orijinalle birebir aynı)
# ──────────────────────────────────────────────────────────────────────────────

def kareleri_ornekle(frames, hedef=HEDEF_KARE):
    if len(frames) == 0:
        return np.zeros((hedef, 201), dtype=np.float32)
    idx = np.linspace(0, len(frames) - 1, hedef).astype(int)
    return np.array([frames[i] for i in idx], dtype=np.float32)


def normalize_201(ham_201):
    norm_kare = np.zeros(201, dtype=np.float32)
    if np.sum(ham_201) == 0:
        return norm_kare
    burun_x, burun_y, burun_z = ham_201[0], ham_201[1], ham_201[2]
    ls_x, ls_y, rs_x, rs_y   = ham_201[33], ham_201[34], ham_201[36], ham_201[37]
    omuz_genisligi = max(np.sqrt((ls_x - rs_x) ** 2 + (ls_y - rs_y) ** 2), 1e-6)
    for j in range(67):
        norm_kare[j*3:j*3+3] = (ham_201[j*3:j*3+3] - [burun_x, burun_y, burun_z]) / omuz_genisligi
    return norm_kare


def msg(tip: str, metin: str) -> str:
    return json.dumps({"type": tip, "text": metin}, ensure_ascii=False)


# ──────────────────────────────────────────────────────────────────────────────
# FASTAPI & WEBSOCKET
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI()


@app.websocket("/ws")
async def isaret_dili_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("📱 Telefon bağlandı! Akış başladı.")

    sekans           = []
    bos_frame_sayisi = 0
    son_tahmin       = ""
    cumle_kelimeler  = []
    nlp_cumlesi      = ""

    try:
        while True:
            # ── 1. Veri alma ─────────────────────────────────────────────
            data = await websocket.receive_text()

            # RESET komutu
            if data.strip().upper() == "RESET":
                sekans, bos_frame_sayisi = [], 0
                cumle_kelimeler, son_tahmin, nlp_cumlesi = [], "", ""
                await websocket.send_text(msg("reset", ""))
                print("🔄 Sıfırlandı.")
                continue

            # ── 2. Görüntü decode ────────────────────────────────────────
            img_data = base64.b64decode(data)          # orijinalle aynı (validate yok → hızlı)
            np_arr   = np.frombuffer(img_data, np.uint8)
            frame    = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            # ── 3. Görüntü düzeltme ──────────────────────────────────────
            # Telefon ön kamerası 180° ters geliyor
            frame = cv2.rotate(frame, cv2.ROTATE_180)

            # ── 4. Kamera penceresi (debug) ──────────────────────────────
            debug_frame = frame.copy()
            cv2.putText(debug_frame, f"Son: {son_tahmin}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(debug_frame, nlp_cumlesi, (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            cv2.imshow("Sunucu Isleme Ekrani", debug_frame)
            cv2.waitKey(1)

            # ── 5. MediaPipe özellik çıkarımı ────────────────────────────
            # Orijinaldeki gibi 480x360'a resize edilmiş frame kullanıyoruz
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                              data=cv2.resize(rgb, (480, 360)))   # ← kritik hız farkı

            pose_data = np.zeros(75, dtype=np.float32)
            res_pose  = pose_det.detect(mp_img)
            if res_pose.pose_landmarks:
                pose_data = np.array(
                    [[lm.x, lm.y, lm.z] for lm in res_pose.pose_landmarks[0][:25]]
                ).flatten()

            lh_data, rh_data = np.zeros(63), np.zeros(63)
            res_hand = hand_det.detect(mp_img)
            if res_hand.hand_landmarks:
                for lms, info in zip(res_hand.hand_landmarks, res_hand.handedness):
                    coords = np.array([[lm.x, lm.y, lm.z] for lm in lms]).flatten()
                    if info[0].category_name == 'Left':
                        lh_data = coords
                    else:
                        rh_data = coords

            norm_kare = normalize_201(np.concatenate([pose_data, lh_data, rh_data]))
            el_var    = np.any(lh_data) or np.any(rh_data)

            # ── 6. Sekans & tahmin mantığı ───────────────────────────────
            if el_var:
                sekans.append(norm_kare)
                bos_frame_sayisi = 0
            else:
                if len(sekans) > 0:
                    bos_frame_sayisi += 1

            if (len(sekans) >= MIN_SEKANS_KARE and bos_frame_sayisi >= BOS_KARE_ESIGI) \
                    or len(sekans) >= MAX_SEKANS_KARE:

                if len(sekans) >= MIN_SEKANS_KARE:
                    input_data = np.expand_dims(kareleri_ornekle(sekans, HEDEF_KARE), axis=0)
                    preds      = model(input_data, training=False).numpy()[0]
                    idx        = np.argmax(preds)

                    if preds[idx] > GUVEN_ESIGI:
                        kelime = KELIMELER[idx]
                        print(f"🎯 Tahmin: {kelime} (%{preds[idx]*100:.1f})")

                        # Kelimeyi gönder
                        await websocket.send_text(msg("word", kelime))

                        # NLP: aynı kelime art arda eklenmesin
                        if kelime != son_tahmin:
                            cumle_kelimeler.append(kelime)
                            son_tahmin  = kelime
                            nlp_cumlesi = nlp.cumle_kur(cumle_kelimeler)

                        # NLP cümlesini gönder
                        await websocket.send_text(msg("sentence", nlp_cumlesi))

                sekans, bos_frame_sayisi = [], 0

    except WebSocketDisconnect:
        print("❌ Bağlantı kesildi.")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"⚠️ Hata oluştu: {e}")


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)