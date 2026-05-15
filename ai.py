import cv2
import torch
import pandas as pd
import time
import paho.mqtt.client as mqtt
import mqtt_pub
import config
from datetime import datetime
import asyncio
from ultralytics import YOLO

def setup_camera():
    cap = cv2.VideoCapture(config.settings.CAMERA_ID)
    # カメラの解像度設定
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 448)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 448)
    return cap

async def detect_objects(model, frame, imagsz=420, conf=0.6, classes=None, verbose=False):
    conf = float(conf)
    # imgsz=320で軽量化。conf=0.6で誤検出を抑制
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    input_frame = cv2.merge([gray_frame, gray_frame, gray_frame])
    results = model(input_frame, imgsz=imagsz, verbose=verbose, conf=conf, classes=classes)

    if results[0].boxes is None or len(results[0].boxes) == 0:
        return pd.DataFrame(), results[0]

    # 検出結果をPandas DataFrameに変換
    df = pd.DataFrame(results[0].boxes.data.cpu().numpy(), columns=[
                      'xmin', 'ymin', 'xmax', 'ymax', 'confidence', 'class'])
    return df, results[0]


async def main():
# def main():
    print("--- 🚀 リアルタイム監視システム起動 ---")
    try:
        # モデルの読み込み
        model_people = YOLO(config.settings.YOLO_AI_MODEL_PASS)
        model_elevator = YOLO(config.settings.ELEVATOR_AI_MODEL_PASS)
        print("✅ モデルのロードに成功しました")

        cap = setup_camera()
        image_size = 448  # 画像サイズを小さくして処理を軽くする
        person_conf = float(0.7)
        elevator_conf = float(0.3)

        client=mqtt_pub.connect_mqtt_publisher()
        time.sleep(2)


        # ログの見出しを表示

        print("\n" + "-" * 60)
        print(f"{'時刻':<10} | {'人数':<4} | {'表示内容':<15} | {'方向'} | {'確信度'}")
        print("-" * 60)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("❌ カメラからフレームを取得できませんでした。終了します。")
                break

            # --- AI検出実行 ---
            result =await asyncio.gather(
                detect_objects(model_people, frame, imagsz=image_size, conf=person_conf, classes=[0]),  # クラス0は通常 'person'
                detect_objects(model_elevator, frame, imagsz=image_size, conf=elevator_conf)  # エレベーターは全クラス対象
            )

            df_people, res_p = result[0]
            df_elevator, res_e = result[1]

            people_count = len(df_people)

            # 1. 人数のカウント (クラス0が通常 'person')
            # results_p = model_people(frame, imgsz=320, verbose=False, conf=0.6, classes=[0])
            # res_p = results_p[0]

            # if res_p.boxes is not None:
            #     df_people = pd.DataFrame(res_p.boxes.data.cpu().numpy(), columns=[
            #                             'xmin', 'ymin', 'xmax', 'ymax', 'confidence', 'class'])
            #     people_count = len(df_people)
            # else:
            #     df_people = pd.DataFrame()
            #     people_count = 0
            # 2. エレベーター情報の取得（数字と矢印の両方に対応）
            elevator_floor = 0
            direction = 0
            max_conf = 0.0

            if not df_elevator.empty:
                # 全ての検出結果をループでチェックする
                for _, row in df_elevator.iterrows():
                    class_id = int(row['class'])
                    label = model_elevator.names[class_id]
                    conf = row['confidence']

                    # スコアが一番高いものをログ用の確信度にする
                    if conf > max_conf:
                        max_conf = conf

                    # ラベルが数字（'9','10'など）か判定
                    if label.isdigit():
                        elevator_floor = label.strip()
                    # ラベルが矢印（'up','down'）か判定
                    
                    if label in ['up', 'down']:
                        direction = label


            # 3. ターミナルへのログ出力
            now = datetime.now()
            now_str = now.strftime(f"%Y/%m/%d  %H:%M:%S")
            print(f"{now_str} | {people_count}人 | {elevator_floor} | {direction} | {max_conf:.2f}")

            asyncio.gather(mqtt_pub.publish_elevator_status(client, config.settings.MQTT_TOPIC, config.settings.DEVICE_ID,elevator_floor,people_count,direction))
            #client, topic, elevator_id,current_floor,occupancy,direction

            # 表示用のテキストを合成（例: "9 up"）
            display_floor = f"{elevator_floor} ".strip()
            # 4. 画面描画
            # 人物の検出枠を描画
            annotated_frame = res_p.plot()
            # エレベーター（数字・矢印）の検出枠を上書き描画
            if not df_elevator.empty:
                annotated_frame = res_e.plot(img=annotated_frame)

            # 左上に情報を表示
            info_text = f"People: {people_count}  Floor: {display_floor} direction: {direction}"
            cv2.putText(annotated_frame, info_text, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # 5. ウィンドウ表示
            cv2.imshow("Real-time AI Monitor", annotated_frame)

            # 'q' キーで終了
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # 後片付け
    except Exception as e:
        print(f"❌ エラー: {e}")
    except KeyboardInterrupt:
        print("\n--- ⌨️ キーボード割り込みで終了 ---")
        cap.release()
        cv2.destroyAllWindows()
        print("\n--- 👋 システムを終了しました ---")

if __name__ == "__main__":
    asyncio.run(main())




