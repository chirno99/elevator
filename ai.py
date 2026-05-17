import cv2
# import torch
import pandas as pd
import time
# import paho.mqtt.client as mqtt
import mqtt_pub
import config
from datetime import datetime
import asyncio
from ultralytics import YOLO

def setup_camera(): # カメラの初期化
    cap = cv2.VideoCapture(config.settings.CAMERA_ID)
    # カメラの解像度設定
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 448)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 448)
    return cap

async def detect_objects(model, frame, imagsz=420, conf=0.6, classes=None, verbose=False): # AIモデルを使ってフレームから物体を検出する関数
    conf = float(conf)
    # imgsz=320で軽量化。conf=0.6で誤検出を抑制
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # グレースケールに変換してモデルに入力（YOLOは通常3チャンネルの画像を想定しているため、グレースケールを3チャンネルに変換）
    input_frame = cv2.merge([gray_frame, gray_frame, gray_frame]) # グレースケールを3チャンネルに変換
    results = model(input_frame, imgsz=imagsz, verbose=verbose, conf=conf, classes=classes) # モデルで物体検出を実行

    if results[0].boxes is None or len(results[0].boxes) == 0: # 検出結果がない場合は空のDataFrameを返す
        return pd.DataFrame(), results[0]

    # 検出結果をPandas DataFrameに変換
    df = pd.DataFrame(results[0].boxes.data.cpu().numpy(), columns=[ # YOLOの検出結果をDataFrameに変換
                      'xmin', 'ymin', 'xmax', 'ymax', 'confidence', 'class'])
    return df, results[0] # DataFrameとYOLOの結果オブジェクトを返す


def judgementElecator(df_elevator, model_elevator, max_conf): # エレベーターの表示内容と方向を判定する関数
    elevator_floor = 0 # エレベーターの表示内容（階数）を初期化
    direction = 0 # エレベーターの方向を初期化
    result_conf = 0.0 # エレベーターの検出結果
    
    if not df_elevator.empty: # エレベーターの検出結果がある場合
        # 全ての検出結果をループでチェックする
        for _, row in df_elevator.iterrows():
            class_id = int(row['class'])
            label = model_elevator.names[class_id]
            conf = row['confidence']

            # スコアが一番高いものをログ用の確信度にする
            if conf > max_conf:
                result_conf = conf

            # ラベルが数字（'9','10'など）か判定
            if label.isdigit():
                elevator_floor = label.strip()
            # ラベルが矢印（'up','down'）か判定
            
            if label in ['up', 'down']:
                direction = label
        return [elevator_floor, direction, result_conf]
    else:
        return [elevator_floor, direction, result_conf]
    

    
async def main():
# def main():
    try:
        image_size = 448  # 画像サイズを小さくして処理を軽くする
        max_conf = 0.0 # エレベーターの検出結果の中で最も高い確信度を記録する変数
        person_conf = float(0.7) # 人物検出の信頼度の閾値を0.7に設定（誤検出を減らすため）
        elevator_conf = float(0.3) # エレベーターの数字・矢印検出の信頼度の閾値を0.3に設定（小さめにして見逃しを減らすため）
        client_id="elevator_publisher"
        
        print("--- 🚀 リアルタイム監視システム起動 ---")
        # モデルの読み込み
        print("\n⏳ モデルをロードしています...")
        model_people =YOLO(config.settings.YOLO_AI_MODEL_PASS)  # 人物検出用のモデルをロード
        model_elevator = YOLO(config.settings.ELEVATOR_AI_MODEL_PASS)  # エレベーターの数字・矢印検出用のモデルをロード
        print("\n✅ モデルのロードに成功しました")

        print("\n⏳ カメラを初期化しています...")
        cap = setup_camera()
        print ("\n✅ カメラの初期化に成功しました")
        
        # MQTTクライアントの接続
        print("\n⏳ MQTTクライアントを接続しています...")
        
        client=mqtt_pub.connect_mqtt_publisher(client_id)
        
        if client is None or not client.is_connected(): 
            print("\n❌ MQTTクライアントの接続に失敗しました")
            print("\n ⏳ MQTTクライアントの再接続を試みます...")
            client=mqtt_pub.connect_mqtt_publisher(client_id)
            
        # time.sleep(2)  # 接続が安定するまで少し待つ
        
        # ログの見出しを表示
        print("\n" + "-" * 60)
        print(f"{'時刻':<10} | {'人数':<4} | {'表示内容':<15} | {'方向'} | {'信用度'}")
        print("-" * 60)

        while cap.isOpened(): # カメラが開いているどうか
            try:
                # 2. エレベーター情報の取得（数字と矢印の両方に対応）
                elevator_floor = 0
                direction = 0
                ret, frame = await asyncio.get_event_loop().run_in_executor(None, cap.read) # カメラからフレームを読み込む
                if not ret:
                    print("❌ カメラからフレームを取得できませんでした。終了します。")
                    continue
                
                # time.sleep(0.5) # 遅延を擬似再現
                
                # --- AI検出実行 ---
                result =await asyncio.gather(
                    detect_objects(model_people, frame, imagsz=image_size, conf=person_conf, classes=[0]),  # クラス0は通常 'person'
                    detect_objects(model_elevator, frame, imagsz=image_size, conf=elevator_conf)  # エレベーターは全クラス対象
                )
                # time.sleep(0.6) # 遅延を擬似再現
                df_people, res_p = result[0] # 人物検出の結果
                df_elevator, res_e = result[1] # エレベーター検出の結果
                people_count = len(df_people) # 人数をカウント
                
                elevator_floor, direction, result_conf = judgementElecator(df_elevator, model_elevator, max_conf) # エレベーターの表示内容と方向を判定
                
                # 3. ターミナルへのログ出力
                now = datetime.now()
                now_str = now.strftime(f"%Y/%m/%d  %H:%M:%S")
                print(f"{now_str} | {people_count}人 | {elevator_floor} | {direction} | {result_conf:.2f}")

                asyncio.gather(mqtt_pub.publish_elevator_status(client, config.settings.MQTT_TOPIC, config.settings.DEVICE_ID,elevator_floor,people_count,direction)) # MQTTでエレベーターの状態を送信
                # time.sleep(0.3) # 遅延を擬似再現
                #client, topic, elevator_id,current_floor,occupancy,direction

                # asyncio.gather(display_window(elevator_floor, direction, people_count, df_elevator, res_p, res_e)) # ウィンドウに情報を表示
                
                #  ---------------ウィンドウを画面に表示する---------------
                
                # 表示用のテキストを合成（例: "9 up"）
                display_floorwindow = f"{elevator_floor} ".strip()
                # 4. 画面描画
                # 人物の検出枠を描画
                annotated_frame = res_p.plot()
                # エレベーター（数字・矢印）の検出枠を上書き描画
                
                annotated_frame = res_e.plot(img=annotated_frame)

                # 左上に情報を表示
                info_text = f"People: {people_count}  Floor: {display_floorwindow} direction: {direction}" 
                
                cv2.putText(
                    annotated_frame, info_text, (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
                )

                # 5. ウィンドウ表示
                cv2.imshow("Real-time AI Monitor", annotated_frame)

                # 'q' キーで終了
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                # ---------------ウィンドウを画面に表示する---------------
            # 後片付け
            except Exception as e:
                print(f"❌ エラー: {e}")
            except KeyboardInterrupt:
                print("\n--- ⌨️ キーボード割り込みで終了 ---")
                cap.release()
                cv2.destroyAllWindows()
                print("\n--- 👋 システムを終了しました ---")

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