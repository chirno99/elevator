import ultralytics
import os
import config

def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(project_root, 'datasets_250117', 'data.yaml') # データセットのYAMLファイルのパスを指定
    images_dir = os.path.join(project_root, 'datasets_250117', 'train', 'images') # トレーニング用画像のディレクトリのパスを指定
    model_name = config.settings.YOLO_AI_MODEL_PASS
    export_model_name = 'elevatorTrackerv8'
    epochs = 200 # エポック数を200に設定（必要に応じて調整してください）
    imgsz = config.settings.TRAIN_IMAGE_SIZE
    batch_size = 16 # VRAMに応じてバッチサイズを調整してください（例: 4GBなら4〜8、8GBなら16、16GB以上なら32〜64）
#   ┌──────────┬────────────┐
#   │   VRAM   │ 推奨 batch │
#   ├──────────┼────────────┤
#   │ 4GB      │ 4〜8       │
#   ├──────────┼────────────┤
#   │ 8GB      │ 16         │
#   ├──────────┼────────────┤
#   │ 16GB以上 │ 32〜64     │
#   └──────────┴────────────┘

    print(f"Project root directory: {project_root}")
    print(f"YAML file path: {yaml_path}")
    print(f"Model name from config: {model_name}")

    ultralytics.checks()

    try:
        import torch
        device = 0 if torch.cuda.is_available() else 'cpu'
    except ImportError:
        device = 'cpu'
    print(f"Using device: {device}")

    # Train
    model = ultralytics.YOLO(model=model_name)
    model.train(data=yaml_path, epochs=epochs, imgsz=imgsz, batch=batch_size, device=device, name=export_model_name, exist_ok=True)

    # Export trained model (model is updated in-place with best weights after training)
    export_path = model.export(format="onnx")
    print(f"Exported model path: {export_path}")

    # Predict using the exported ONNX model
    onnx_model = ultralytics.YOLO(str(export_path))
    test_images_dir = os.path.join(images_dir)  # テスト用画像のディレクトリのパスを指定
    results = onnx_model.predict(source=test_images_dir, conf=0.5, save=True)
    print(f"Prediction complete. Results saved to runs/detect/")

if __name__ == "__main__":
    main()
