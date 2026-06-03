import cv2
import sys

def capture_and_check():
    # ─── 1. カメラの初期化（本番と同じ最高画質設定） ───
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("エラー: カメラを開くことができませんでした。接続を確認してください。")
        sys.exit()
        
    # 解像度を最高画質（1280x720）に固定
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # カメラが安定するまで数フレーム空読み（露出・ピント合わせ用）
    for _ in range(5):
        cap.read()

    # ─── 2. 撮影（現在のリアルタイムな1枚を取得） ───
    ret, frame = cap.read()
    cap.release() # 撮影が終わったらすぐカメラを解放

    if not ret:
        print("エラー: カメラからの画像取得に失敗しました。")
        return

    h, w, _ = frame.shape
    
    # ─── 3. センターラインの描画（白色） ───
    cv2.line(frame, (int(w/2), 0), (int(w/2), h), (255, 255, 255), 1)
    cv2.line(frame, (0, int(h/2)), (w, int(h/2)), (255, 255, 255), 1)
    
    # ─── 4. 手前の枠（LEFT DISP: 確定座標） ───
    left_start = (175, 60)
    left_end = (330, 310)
    cv2.rectangle(frame, left_start, left_end, (0, 255, 0), 2)
    cv2.putText(frame, "TARGET: LEFT DISP", (left_start[0], left_start[1] - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # ─── 5. 奥の枠（RIGHT DISP: 確定座標） ───
    right_width = 45
    center_x = int(w / 2) - int(right_width / 2)
    previous_x = center_x + 100 - 150 + 350 - 130  # 計算ベース位置
    new_moved_x = previous_x + 20                  # 20px右へ移動
    
    right_start = (new_moved_x - 15, 45)
    right_end = (new_moved_x + right_width + 15, 205)
    cv2.rectangle(frame, right_start, right_end, (0, 255, 0), 2)
    cv2.putText(frame, "TARGET: RIGHT DISP", (right_start[0], right_start[1] - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # ─── 6. 画像の保存 ───
    output_filename = 'latest_change.jpg'
    cv2.imwrite(output_filename, frame)
    
    print(f" 📸 画角チェック用画像を生成しました: {output_filename}")

if __name__ == "__main__":
    capture_and_check()