from src.data_loader import DataLoader


def main():
    loader = DataLoader()

    loader.load_parquet(
        parquet_path="files/accounts.parquet",
        table_name="atp_accounts",
    )
    
    loader.load_parquet(
            parquet_path="files/orders.parquet",
            table_name="atp_orders",
        )


if __name__ == "__main__":
    main()