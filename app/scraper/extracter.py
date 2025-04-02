"""Tools for extracting data from .xls files."""

import asyncio
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime as dt
from typing import Any

import pandas as pd
from pandas.core.series import Series

lgr = logging.getLogger(__name__)


def raw_read(file_path: str) -> tuple[dt, int]:
    """
    Read the .xls file to define trade date and header row index.

    Args:
        file_path (str): Absolute path to the processing .xls file.

    Raises:
        ValueError: If keyphrase not found or file contains multiple phrases.

    Returns:
        tuple[datetime, int]: Trade date and column row index.
    """
    df_temp = pd.read_excel(file_path, sheet_name=0, header=None)
    target_date_str = "Дата торгов:"
    mask = df_temp.apply(
        lambda col: col.astype(str).str.contains(target_date_str, na=False)
    )
    # индексы первой найденной ячейки
    row_idx, col_idx = mask.stack()[mask.stack()].index[0]

    # извлечь значение найденной ячейки, преобразовать в дату
    cell_val: str = df_temp.iloc[row_idx, col_idx]
    date: dt = dt.strptime(cell_val.split(":")[-1].strip(), "%d.%m.%Y")

    # поиск строки заголовков через ключевую фразу
    phrase = "Единица измерения: Метрическая тонна"

    # конвертация всего df в строку и поиск ключевой фразы построчно
    phrase_mask = (
        df_temp.astype(str)
        .apply(lambda col: col.str.contains(phrase))
        .any(axis=1)
    )
    phrase_indices = df_temp.index[phrase_mask]

    if len(phrase_indices) == 0:
        raise ValueError(f"Phrase '{phrase}' not foind in '{file_path}'")
    elif len(phrase_indices) > 1:
        raise ValueError(f"Many lines with phrase '{phrase}' in '{file_path}'")

    return date, phrase_indices[0] + 1


def processing_df(file_path: str, start_idx: int) -> pd.DataFrame:
    """
    Normalize dataframe by applying necessary transformations and filters.

    Make some important transformations and main filtering.

    Args:
        file_path (str): Absolute path to the processing .xls file.
        start_idx (int): Header row index.

    Returns:
        pd.DataFrame: Processed dataframe for data extraction.
    """
    # чтение файла с многоуровневыми заголовками по индексам строк
    # замена всех значений "-" на NaN для упрощения дальнейшей обработки df
    df = pd.read_excel(
        file_path,
        sheet_name=0,
        header=[int(start_idx), int(start_idx + 1)],
        na_values="-",
    )

    # определяем столбцы для фильтраций / корректировок
    code_tool_col = ("Код\nИнструмента", "Unnamed: 1_level_1")
    vol_col = ("Объем\nДоговоров\nв единицах\nизмерения", "Unnamed: 4_level_1")
    total_col = ("Обьем\nДоговоров,\nруб.", "Unnamed: 5_level_1")
    contracts_col = ("Количество\nДоговоров,\nшт.", "Unnamed: 14_level_1")

    # оставляем только строки без 'Итого' в столбце 'Код Инструмента'
    df = df[~df[code_tool_col].astype(str).str.contains("Итого", na=False)]

    # удаление строк с NaN в столбце 'Количество договоров, шт'
    df = df.dropna(subset=[contracts_col])

    # приведение столбцов с целочисленными значениями к типу 'Int64' ('int')
    int_columns = [vol_col, total_col, contracts_col]
    df[int_columns] = df[int_columns].astype("Int64")

    lgr.debug(f"Successfully processed file on '{file_path}'")
    return df


def extracting_vals(date: dt, df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Extract required values ​​from the dataframe row by row.

    Args:
        date (dt): Trade date.
        df (pd.DataFrame): Processed dataframe.

    Returns:
        list[dict[str, Any]]: List of dictionaries with extracted row data.
    """
    # получаем нужные столбцы по номерам подзаголовков
    col_exchange_product_id: Series = df.iloc[:, 1]  # Код инструмента
    col_exchange_product_name: Series = df.iloc[:, 2]  # Наименование инстр
    col_delivery_basis_name: Series = df.iloc[:, 3]  # Базис поставки
    col_volume: Series = df.iloc[:, 4]  # Объем договоров в единицах измерения
    col_total: Series = df.iloc[:, 5]  # Объем договоров, руб
    col_count: Series = df.iloc[:, 14]  # Количество договоров, шт

    # объединяем столбцы для построчной обработки
    merger: zip = zip(
        col_exchange_product_id,
        col_exchange_product_name,
        col_delivery_basis_name,
        col_volume,
        col_total,
        col_count,
    )

    # извлекаем требуемые данные
    result = []
    lgr.debug(f"Satrt data receiveng for the date {date}.")
    for i, (prod_id, prod_name, basis, volume, total, count) in enumerate(
        merger, start=1
    ):
        if count <= 0:
            continue

        oil_id = prod_id[:4]
        delivery_basis_id = prod_id[4:7]
        delivery_type_id = prod_id[-1]

        result.append(
            {
                "exchange_product_id": prod_id,
                "exchange_product_name": prod_name,
                "oil_id": oil_id,
                "delivery_basis_id": delivery_basis_id,
                "delivery_type_id": delivery_type_id,
                "delivery_basis_name": basis,
                "volume": int(volume),
                "total": int(total),
                "count": int(count),
                "date": date,
            }
        )
        lgr.debug(f"Line {i} processed successfully.")

    lgr.debug(
        f"Data recieved for the date {date.strftime('%d.%m.%Y')}: "
        f"{i} rows processed successfully."
    )
    return result


def process_file(args: tuple[str, str]) -> list[dict[str, Any]]:
    """
    Process a single .xls file and return the extracted data.

    Args:
        args (tuple[str, str]): Contains dir_path and filename where
            dir_path (str): Directory containing the files.
            filename (str): Name of the file to process.

    Returns:
        list[dict[str, Any]]: Extracted data from the file.
    """
    dir_path, filename = args
    filepath: str = os.path.join(dir_path, filename)

    date, header_start_idx = raw_read(filepath)
    df = processing_df(filepath, header_start_idx)
    data = extracting_vals(date, df)

    lgr.debug(f"Finished processing file: {filename}")
    return data


def main_extract(temp_dir: str) -> list[list[dict[str, Any]]]:
    """
    Run multi-processing file processing and collect data.

    Args:
        temp_dir (str): Absolute path to the directory with files.

    Returns:
        list[list[dict[str, Any]]]: Final result to save to the db.
    """
    files: list[str] = [
        entry.name
        for entry in os.scandir(temp_dir)
        if entry.is_file() and entry.name.endswith((".xls", ".xlsx"))
    ]

    cpu_count: int | None = os.cpu_count()
    if not cpu_count:
        raise OSError("Unable to count the number of processor cores.")

    with ProcessPoolExecutor(max_workers=cpu_count + 1) as executor:
        results = list(
            executor.map(
                process_file, [(temp_dir, file_name) for file_name in files]
            )
        )

    total_rows: int = sum(len(file_data) for file_data in results)
    lgr.debug(
        "All files processed. "
        f"Total files: {len(results)}. Total rows: {total_rows}"
    )
    return results


async def async_extract(temp_dir: str) -> list[list[dict[str, Any]]]:
    """
    Async wrapper for the synchronous main_extract function.

    Args:
        temp_dir (str): Absolute path to the directory with files.

    Returns:
        list[list[dict[str, Any]]]: Final result to save to the db.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, main_extract, temp_dir)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(lineno)d | %(asctime)s | %(name)s | "
        "%(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    start: float = time.time()
    temp_dir: str = os.path.join(os.path.dirname(__file__), "downloads")
    # result_for_db: list[list[dict]] = main_extract(temp_dir)
    result_for_db = asyncio.run(async_extract(temp_dir))
    lgr.debug(f"Lenght of results: {len(result_for_db)}")
    lgr.info(f"Task execution time: {round(time.time() - start, 4)}")
