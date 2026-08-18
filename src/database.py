import os
from pathlib import Path
import pandas as pd
import pymysql
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


class DataLoader:

    def __init__(self):
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "3306"))
        self.db_name = os.getenv("DB_NAME")

        self._validate_config()
        
        # 1. Crear la base de datos si no existe
        self._ensure_database_exists()

        # 2. Inicializar el engine conectando directamente a la BD
        self.engine = create_engine(
            f"mysql+pymysql://"
            f"{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/"
            f"{self.db_name}"
        )

    def _validate_config(self):
        """Validate required database configuration."""
        required_config = {
            "DB_USER": self.db_user,
            "DB_PASSWORD": self.db_password,
            "DB_NAME": self.db_name,
        }

        missing_config = [
            key for key, value in required_config.items() if not value
        ]

        if missing_config:
            raise ValueError(
                f"Missing environment variables: {', '.join(missing_config)}"
            )

    def _ensure_database_exists(self):
        """Conecta al servidor MySQL y crea la base de datos objetivo si no existe."""
        connection = pymysql.connect(
            host=self.db_host,
            user=self.db_user,
            password=self.db_password,
            port=self.db_port,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}`;")
            connection.commit()
            print(f"Base de datos '{self.db_name}' verificada/creada exitosamente.")
        finally:
            connection.close()

    def load_parquet(
        self,
        parquet_path: str,
        table_name: str,
        if_exists: str = "replace",
        chunksize: int = 50_000,
    ):
        """Load a Parquet file into a SQL table."""
        parquet_path = Path(parquet_path)

        if not parquet_path.exists():
            raise FileNotFoundError(
                f"Parquet file not found: {parquet_path}"
            )

        print(f"Reading Parquet file: {parquet_path}")
        df = pd.read_parquet(parquet_path)

        print(f"Rows: {len(df):,}")
        print(f"Columns: {len(df.columns)}")

        print(f"Loading data into SQL table: {table_name}")

        df.to_sql(
            name=table_name,
            con=self.engine,
            if_exists=if_exists,
            index=False,
            chunksize=chunksize,
            method="multi",
        )

        print(
            f"Successfully loaded {len(df):,} rows into '{table_name}'"
        )