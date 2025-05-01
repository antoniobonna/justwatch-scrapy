# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import re
from datetime import datetime
from typing import Any, Optional

import pandas as pd
from sqlalchemy import create_engine


class GraphQLPostgreSQLPipeline:
    """
    Pipeline to store scraped items from the GraphQL API in a PostgreSQL database.

    This pipeline saves items to PostgreSQL using pandas and SQLAlchemy.
    """

    def __init__(self, postgres_uri: str, table_name: str, schema: str, batch_size: int = 100):
        """
        Initializes the PostgreSQL pipeline.

        Args:
            postgres_uri (str): Connection URI for PostgreSQL
            table_name (str): Name of the table to store the data
            schema (str): Name of the schema in the database
            batch_size (int, optional): Number of items to collect before batch saving.
        """
        self.postgres_uri = postgres_uri
        self.table_name = table_name
        self.schema = schema
        self.batch_size = batch_size
        self.items: list[dict[str, Any]] = []
        self.engine = None

    @classmethod
    def from_crawler(cls, crawler):
        """
        Creates an instance from a crawler.

        This method is used by Scrapy to create your pipeline instance
        and connect it to the crawler process.

        Args:
            crawler: The crawler controlling this pipeline

        Returns:
            GraphQLPostgreSQLPipeline: A new instance of the pipeline
        """
        return cls(
            postgres_uri=crawler.settings.get("POSTGRES_URI"),
            table_name=crawler.settings.get("POSTGRES_TABLE"),
            schema=crawler.settings.get("POSTGRES_SCHEMA"),
            batch_size=crawler.settings.get("POSTGRES_BATCH_SIZE"),
        )

    def open_spider(self, spider):
        """
        Initializes resources when the spider starts.

        Args:
            spider: The spider being started
        """
        # Create SQLAlchemy engine on initialization
        self.engine = create_engine(self.postgres_uri)
        self.items = []
        spider.logger.info(f"PostgreSQL connection established: {self.postgres_uri}")

        try:
            with self.engine.connect() as conn:
                spider.logger.info("Connection test successful")
        except Exception as e:
            spider.logger.error(f"Connection test failed: {e}")

    def process_item(self, item, spider):
        """
        Processes an item scraped by the spider.

        Args:
            item: The scraped item
            spider: The spider that scraped the item

        Returns:
            dict: The processed item
        """
        # Add item to the list
        self.items.append(dict(item))

        # If the batch size is reached, save to the database
        if len(self.items) >= self.batch_size:
            self.save_items(spider)
            self.items = []  # Clear the list after saving

        return item

    def save_items(self, spider):
        """
        Saves the collected items to the database.

        Args:
            spider: The spider that scraped the items
        """
        if not self.items:
            return

        try:
            # Create DataFrame with the current batch
            df = pd.DataFrame(self.items)

            # Process the data before saving
            if not df.empty:
                df = self.process_dataframe(df)

            # Save to PostgreSQL
            df.to_sql(
                name=self.table_name,
                schema=self.schema,
                con=self.engine,
                if_exists="append",  # Append data to the existing table
                index=False,
            )

            spider.logger.info(f"{len(self.items)} items saved to table '{self.table_name}'")

            # Clear the item list after saving
            self.items = []

        except Exception as e:
            spider.logger.error(f"Error saving data to PostgreSQL: {e}")
            raise  # Re-raise the exception for Scrapy to handle (if needed)

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes the dataframe to clean and transform the data.

        Transformations:
        1.  Converts the `duracao_minutos` column to the '%h %min' format.
        2.  Ensures null values are handled correctly.
        3.  Adds the 'extract_timestamp' column.

        Args:
            df: The dataframe to be processed

        Returns:
            The processed dataframe
        """
        df_processed = df.copy()

        # 1. Convert duracao_minutos to '%h %min' format
        df_processed["duracao"] = df_processed["duracao_minutos"].apply(self._format_duration)

        # 2. Ensure null values are handled correctly.
        df_processed = df_processed.map(lambda x: pd.NA if x == "" else x)

        # 3. Add timestamp column
        df_processed["extract_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return df_processed

    def _format_duration(self, minutes: Any) -> Optional[str]:
        """
        Formats the duration in minutes to the '%h %min' format.

        Args:
            minutes: The duration in minutes (int or float)

        Returns:
            The formatted duration as a string ('%h %min') or None if invalid.
        """
        if pd.isna(minutes):
            return None

        try:
            minutes_int = int(minutes)  # Ensure minutes is an integer
            hours = minutes_int // 60
            remaining_minutes = minutes_int % 60
            if hours > 0 and remaining_minutes > 0:
                return f"{hours}h {remaining_minutes}min"
            elif hours > 0:
                return f"{hours}h"
            elif remaining_minutes > 0:
                return f"{remaining_minutes}min"
            else:
                return "0min"
        except (ValueError, TypeError):
            return None

    def close_spider(self, spider):
        """
        Cleans up resources when the spider closes.

        Args:
            spider: The spider being closed
        """
        # Save any remaining items
        self.save_items(spider)

        # Close the database connection
        if self.engine:
            self.engine.dispose()
        spider.logger.info("PostgreSQL Pipeline closed")


class PostgreSQLPipeline:
    """
    Pipeline for storing scraped items in a PostgreSQL database.

    This pipeline collects scraped items in batches and saves them to a
    PostgreSQL database using pandas and SQLAlchemy. It also provides
    data processing functionality to clean and transform the data.
    """

    def __init__(self, postgres_uri: str, table_name: str, schema: str, batch_size: int = 100):
        """
        Initialize the PostgreSQL pipeline.

        Args:
            postgres_uri (str): Connection URI for PostgreSQL
            table_name (str): Name of the table to store data
            batch_size (int, optional): Number of items to collect before batch saving.
        """
        self.postgres_uri = postgres_uri
        self.table_name = table_name
        self.schema = schema
        self.batch_size = batch_size
        self.items: list[dict[str, Any]] = []
        self.engine = None

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create an instance from a crawler.

        This method is used by Scrapy to create your pipeline instance
        and connect it to the crawler process.

        Args:
            crawler: The crawler controlling this pipeline

        Returns:
            PostgreSQLPipeline: A new instance of the pipeline
        """
        return cls(
            postgres_uri=crawler.settings.get("POSTGRES_URI"),
            table_name=crawler.settings.get("POSTGRES_TABLE"),
            schema=crawler.settings.get("POSTGRES_SCHEMA"),
            batch_size=crawler.settings.get("POSTGRES_BATCH_SIZE"),
        )

    def open_spider(self, spider):
        """
        Initialize resources when the spider starts.

        Args:
            spider: The spider being started
        """
        # Create SQLAlchemy engine on initialization
        self.engine = create_engine(self.postgres_uri)
        self.items = []
        spider.logger.info(f"PostgreSQL connection established: {self.postgres_uri}")

        try:
            with self.engine.connect() as conn:
                spider.logger.info("Connection test successful")
        except Exception as e:
            spider.logger.error(f"Connection test failed: {e}")

    def process_item(self, item, spider):
        """
        Process an item scraped by the spider.

        Args:
            item: The scraped item
            spider: The spider which scraped the item

        Returns:
            item: The processed item
        """
        # Add item to list
        self.items.append(dict(item))

        # If batch size is reached, save to database
        if len(self.items) >= self.batch_size:
            self.save_items(spider)

        return item

    def save_items(self, spider):
        """
        Save the collected items to the database.

        Args:
            spider: The spider which scraped the items
        """
        if not self.items:
            return

        try:
            # Create DataFrame with current batch
            df = pd.DataFrame(self.items)

            # Process data before saving
            if not df.empty:
                df = self.process_dataframe(df)

            # Save to PostgreSQL
            df.to_sql(
                name=self.table_name,
                schema=self.schema,
                con=self.engine,
                if_exists="append",  # Append data to existing table
                index=False,
            )

            spider.logger.info(f"{len(self.items)} items saved to table '{self.table_name}'")

            # Clear item list after saving
            self.items = []

        except Exception as e:
            spider.logger.error(f"Error saving data to PostgreSQL: {e}")

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process the dataframe to clean and transform data.

        Transformations:
        1. Apply strip to string columns
        2. Clean and convert year column
        3. Split imdb_score into score (float) and count (int)
        4. Create duration_minutes column from duration

        Args:
            df: The dataframe to process

        Returns:
            The processed dataframe
        """
        # Create a copy to avoid modifying the original dataframe
        df_processed = df.copy()

        # 1. Apply strip to text columns
        text_columns = ["ano", "titulo", "duracao", "classificacao", "sinopse", "imdb_score"]

        for col in text_columns:
            if col in df_processed.columns:
                df_processed[col] = df_processed[col].astype(str).str.strip().replace("None", pd.NA)

        # 2. Clean and convert year column
        df_processed["ano"] = (
            df_processed["ano"]
            .str.replace("(", "")
            .str.replace(")", "")
            .replace("", pd.NA)
            .astype("Int64")
        )

        # 3. Process IMDB score and count
        score_columns = ["imdb_score"]
        for col in score_columns:
            # Create copy to avoid SettingWithCopyWarning
            temp_series = df_processed[col].copy()

            # Process only non-null and non-empty values
            mask = temp_series.notna() & (temp_series.str.strip() != "")

            # Extract score (value before space)
            temp_score = temp_series[mask].astype(str).str.split(" ").str[0].astype(float)

            # Extract count (value in parentheses)
            count_col = "imdb_count"
            df_processed[count_col] = None  # Initialize column

            # Apply regex only where there are valid values
            df_processed.loc[mask, count_col] = temp_series[mask].str.extract(r"\((.*?)\)")[0]

            # Convert k/m notation to integers
            df_processed[count_col] = df_processed[count_col].apply(
                lambda x: self._convert_count_to_int(x)
                if pd.notna(x) and str(x).strip() != ""
                else None
            )
            df_processed[count_col] = df_processed[count_col].astype("Int64")

            # Replace original score column with cleaned value
            df_processed[col] = temp_score

        # 4. Process duration
        duration_columns = ["duracao"]
        for col in duration_columns:
            # Create minutes column
            minutes_col = f"{col}_minutos"
            df_processed[minutes_col] = df_processed[col].apply(self._convert_to_minutes)
            df_processed[minutes_col] = df_processed[minutes_col].astype("Int64")

        # 5. Add timestamp column
        df_processed["extract_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return df_processed

    def _convert_count_to_int(self, value: Any) -> Optional[int]:
        """
        Convert count strings with k/m notation to integers.

        Examples:
            '10k' -> 10000
            '1.5m' -> 1500000
            '123' -> 123

        Args:
            value: The value to convert

        Returns:
            Integer value or None for invalid/empty values
        """
        if pd.isna(value):
            return None

        if not isinstance(value, str):
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        try:
            if "k" in value.lower():
                return int(float(value.lower().replace("k", "")) * 1000)
            elif "m" in value.lower():
                return int(float(value.lower().replace("m", "")) * 1000000)
            else:
                return int(float(value))
        except (ValueError, TypeError):
            return None

    def _convert_to_minutes(self, duration: Any) -> Optional[int]:
        """
        Convert duration string in format 'Xh Ymin' to total minutes.

        Examples:
            '2h 30min' -> 150
            '1h' -> 60
            '45min' -> 45

        Args:
            duration: The duration string to convert

        Returns:
            Total minutes as integer or None for invalid format
        """
        if pd.isna(duration) or not isinstance(duration, str):
            return None

        # Extract hours and minutes using regex
        pattern = r"(\d+)h\s*(\d*)min"
        result = re.search(pattern, duration)

        if result:
            hours = int(result.group(1))
            # If no minutes specified after hours, consider as 0
            minutes = int(result.group(2)) if result.group(2) else 0
            return hours * 60 + minutes

        # Case with only minutes (no hours)
        minutes_pattern = r"(\d+)min"
        result = re.search(minutes_pattern, duration)
        if result:
            return int(result.group(1))

        return None

    def close_spider(self, spider):
        """
        Clean up resources when the spider closes.

        Args:
            spider: The spider being closed
        """
        # Save remaining items
        self.save_items(spider)

        # Close database connection
        if self.engine:
            self.engine.dispose()

        spider.logger.info("PostgreSQL Pipeline closed")
