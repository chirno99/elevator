from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# プロジェクトのルートディレクトリを指定
BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    """ 環境変数を管理するためのPydanticモデル """

    # MQTT接続情報
    MQTT_HOST: str
    MQTT_PORT: int
    MQTT_TOPIC: str
    DEVICE_ID: str
    CAMERA_ID: int = 0
    AI_MODEL_PATH: str
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), # .envファイルの場所を指定
        extra='ignore' # 定義されていない環境変数があっても無視する
    )

# 設定をアプリケーション全体で利用できるようにインスタンス化
settings = Settings()
