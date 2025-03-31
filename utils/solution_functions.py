import feedparser
from urllib.parse import urlencode
import requests
import subprocess
import hashlib
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import zipfile
import pandas as pd
import os
import gzip
import re
import json
from utils.file_process import unzip_folder


def vs_code_version():
    return """
    Version:          Code 1.98.2 (ddc367ed5c8936efe395cffeec279b04ffd7db78, 2025-03-12T13:32:45.399Z)
    OS Version:       Linux x64 6.12.15-200.fc41.x86_64
    CPUs:             11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz (8 x 1300)
    Memory (System):  7.40GB (3.72GB free)
    Load (avg):       3, 2, 2
    VM:               0%
    Screen Reader:    no
    Process Argv:     --crash-reporter-id 80b4d7e7-0056-4767-b601-6fcdbec0b54d
    GPU Status:       2d_canvas:                              enabled
                    canvas_oop_rasterization:               enabled_on
                    direct_rendering_display_compositor:    disabled_off_ok
                    gpu_compositing:                        enabled
                    multiple_raster_threads:                enabled_on
                    opengl:                                 enabled_on
                    rasterization:                          enabled
                    raw_draw:                               disabled_off_ok
                    skia_graphite:                          disabled_off
                    video_decode:                           enabled
                    video_encode:                           disabled_software
                    vulkan:                                 disabled_off
                    webgl:                                  enabled
                    webgl2:                                 enabled
                    webgpu:                                 disabled_off
                    webnn:                                  disabled_off

    CPU %	Mem MB	   PID	Process
        2	   189	 18772	code main
        0	    45	 18800	   zygote
        2	   121	 19189	     gpu-process
        0	    45	 18801	   zygote
        0	     8	 18825	     zygote
        0	    61	 19199	   utility-network-service
        0	   106	 20078	ptyHost
        2	   114	 20116	extensionHost [1]
    21	   114	 20279	shared-process
        0	     0	 20778	     /usr/bin/zsh -i -l -c '/usr/share/code/code'  -p '"0c1d701e5812" + JSON.stringify(process.env) + "0c1d701e5812"'
        0	    98	 20294	fileWatcher [1]

    Workspace Stats:
    |  Window (● solutions.py - tdsproj2 - python - Visual Studio Code)
    |    Folder (tdsproj2): 6878 files
    |      File types: py(3311) pyc(876) pyi(295) so(67) f90(60) txt(41) typed(36)
    |                  csv(31) h(28) f(23)
    |      Conf files:
    """


def make_http_requests_with_uv(
    url="https://httpbin.org/get",
    query_params={"email": "21f2001402@ds.study.iitm.ac.in"},
):
    try:
        response = requests.get(url, params=query_params)
        return response.json()
    except requests.RequestException as e:
        print(f"HTTP request failed: {e}")
        return None


def run_command_with_npx(arguments):
    filePath, prettier_version, hash_algo, use_npx = (
        "README.md",
        "3.4.2",
        "sha256",
        True,
    )
    filePath, prettier_version, hash_algo, use_npx = (
        arguments["filePath"],
        arguments["prettier_version"],
        arguments["hash_algo"],
        arguments["use_npx"],
    )
    prettier_cmd = (
        ["npx", "-y", f"prettier@{prettier_version}", filePath]
        if use_npx
        else ["prettier", filePath]
    )

    try:
        prettier_process = subprocess.run(
            prettier_cmd, capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        print("Error running Prettier:", e)
        return None

    formatted_content = prettier_process.stdout.encode()

    try:
        hasher = hashlib.new(hash_algo)
        hasher.update(formatted_content)
        return hasher.hexdigest()
    except ValueError:
        print(f"Invalid hash algorithm: {hash_algo}")
        return None


def use_google_sheets(
    rows=100, cols=100, start=15, step=12, extract_rows=1, extract_cols=10
):
    matrix = np.arange(start, start + (rows * cols * step), step).reshape(rows, cols)

    extracted_values = matrix[:extract_rows, :extract_cols]

    return np.sum(extracted_values)


def calculate_spreadsheet_formula(formula: str, type: str) -> str:
    try:
        if formula.startswith("="):
            formula = formula[1:]

        if "SEQUENCE" in formula and type == "google_sheets":
            # Example: SUM(ARRAY_CONSTRAIN(SEQUENCE(100, 100, 5, 2), 1, 10))
            sequence_pattern = r"SEQUENCE\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)"
            match = re.search(sequence_pattern, formula)

            if match:
                rows = int(match.group(1))
                cols = int(match.group(2))
                start = int(match.group(3))
                step = int(match.group(4))

                # Generate the sequence
                sequence = []
                value = start
                for _ in range(rows):
                    row = []
                    for _ in range(cols):
                        row.append(value)
                        value += step
                    sequence.append(row)

                # Check for ARRAY_CONSTRAIN
                constrain_pattern = r"ARRAY_CONSTRAIN\([^,]+,\s*(\d+),\s*(\d+)\)"
                constrain_match = re.search(constrain_pattern, formula)

                if constrain_match:
                    constrain_rows = int(constrain_match.group(1))
                    constrain_cols = int(constrain_match.group(2))

                    # Apply constraints
                    constrained = []
                    for i in range(min(constrain_rows, len(sequence))):
                        row = sequence[i][:constrain_cols]
                        constrained.extend(row)

                    if "SUM(" in formula:
                        return str(sum(constrained))

        elif "SORTBY" in formula and type == "excel":
            # Example: SUM(TAKE(SORTBY({1,10,12,4,6,8,9,13,6,15,14,15,2,13,0,3}, {10,9,13,2,11,8,16,14,7,15,5,4,6,1,3,12}), 1, 6))

            # Extract the arrays from SORTBY
            arrays_pattern = r"SORTBY\(\{([^}]+)\},\s*\{([^}]+)\}\)"
            arrays_match = re.search(arrays_pattern, formula)

            if arrays_match:
                values = [int(x.strip()) for x in arrays_match.group(1).split(",")]
                sort_keys = [int(x.strip()) for x in arrays_match.group(2).split(",")]

                # Sort the values based on sort_keys
                sorted_pairs = sorted(zip(values, sort_keys), key=lambda x: x[1])
                sorted_values = [pair[0] for pair in sorted_pairs]

                # Check for TAKE
                take_pattern = r"TAKE\([^,]+,\s*(\d+),\s*(\d+)\)"
                take_match = re.search(take_pattern, formula)

                if take_match:
                    take_start = int(take_match.group(1))
                    take_count = int(take_match.group(2))

                    # Apply TAKE function
                    taken = sorted_values[take_start - 1 : take_start - 1 + take_count]

                    # Check for SUM
                    if "SUM(" in formula:
                        return str(sum(taken))

        return "Could not parse the formula or unsupported formula type"

    except Exception as e:
        return f"Error calculating spreadsheet formula: {str(e)}"


def use_excel(values=None, sort_keys=None, num_rows=1, num_elements=9):
    if values is None:
        values = np.array([13, 12, 0, 14, 2, 12, 9, 15, 1, 7, 3, 10, 9, 15, 2, 0])
    if sort_keys is None:
        sort_keys = np.array([10, 9, 13, 2, 11, 8, 16, 14, 7, 15, 5, 4, 6, 1, 3, 12])

    sorted_values = values[np.argsort(sort_keys)]
    return np.sum(sorted_values[:num_elements])


def use_devtools(html=None, input_name=None):
    if html is None:
        html = '<input type="hidden" name="secret" value="12345">'
    if input_name is None:
        input_name = "secret"

    soup = BeautifulSoup(html, "html.parser")
    hidden_input = soup.find("input", {"type": "hidden", "name": input_name})

    return hidden_input["value"] if hidden_input else None


def count_wednesdays(start_date="1990-04-08", end_date="2008-09-29", weekday=2):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    count = sum(
        1
        for _ in range((end - start).days + 1)
        if (start + timedelta(_)).weekday() == weekday
    )
    return count


def extract_csv_from_a_zip(
    zip_path,
    extract_to="extracted_files",
    csv_filename="extract.csv",
    column_name="answer",
):
    os.makedirs(extract_to, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

    csv_path = os.path.join(extract_to, csv_filename)

    if not os.path.exists(csv_path):
        for root, _, files in os.walk(extract_to):
            for file in files:
                if file.lower().endswith(".csv"):
                    csv_path = os.path.join(root, file)
                    break

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if column_name in df.columns:
            return ", ".join(map(str, df[column_name].dropna().tolist()))

    return ""


def use_json(jsonStr, fields=["age", "name"]):
    data = json.loads(jsonStr)
    sorted_data = sorted(data, key=lambda x: tuple(x[field] for field in fields))
    return json.dumps(sorted_data, separators=(",", ":"))


def multi_cursor_edits_to_convert_to_json(textfile=""):
    result = {}
    lines = textfile.strip().split("\n")
    for line in lines:
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value

    return json.dumps(result)


def css_selectors(file, attribute, cssSelector):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(file, "html.parser")

    elements = soup.select(cssSelector)

    total = 0

    for element in elements:
        value = element.get(attribute)

        if value and value.isdigit():
            total += int(value)

    return total


def process_files_with_different_encodings(file, symbols=["‚", "ˆ", "‡"]):
    extract_dir, file_names = unzip_folder(file)

    total_sum = 0

    try:
        df1 = pd.read_csv(os.path.join(extract_dir, "data1.csv"), encoding="cp1252")
        filtered_df1 = df1[df1["symbol"].isin(symbols)]
        total_sum += filtered_df1["value"].astype(float).sum()
    except Exception as e:
        print(f"Error processing data1.csv: {e}")

    try:
        df2 = pd.read_csv(os.path.join(extract_dir, "data2.csv"), encoding="utf-8")
        filtered_df2 = df2[df2["symbol"].isin(symbols)]
        total_sum += filtered_df2["value"].astype(float).sum()
    except Exception as e:
        print(f"Error processing data2.csv: {e}")

    try:
        df3 = pd.read_csv(
            os.path.join(extract_dir, "data3.txt"), encoding="utf-16", sep="\t"
        )
        filtered_df3 = df3[df3["symbol"].isin(symbols)]
        total_sum += filtered_df3["value"].astype(float).sum()
    except Exception as e:
        print(f"Error processing data3.txt: {e}")

    return int(total_sum) if total_sum.is_integer() else total_sum


def use_github():
    return ""


def replace_across_files(file,string_to_replace, replacement_string,hashing_algo="sha256"):
    
    return ""


def list_files_and_attributes():
    return ""


def move_and_rename_files():
    return ""


def compare_files():
    return ""


def sql_ticket_sales():
    return ""


def write_documentation_in_markdown():
    return ""


def compress_an_image():
    return ""


def host_your_portfolio_on_github_pages():
    return ""


def use_google_colab():
    return ""


def use_an_image_library_in_google_colab():
    return ""


def deploy_a_python_api_to_vercel():
    return ""


def create_a_github_action():
    return ""


def push_an_image_to_docker_hub():
    return ""


def write_a_fastapi_server_to_serve_data():
    return ""


def run_a_local_llm_with_llamafile():
    return ""


def llm_sentiment_analysis():
    return ""


def llm_token_cost():
    return ""


def generate_addresses_with_llms():
    return ""


def llm_vision():
    return ""


def llm_embeddings():
    return ""


def embedding_similarity(embeddings):
    phrases = list(embeddings.keys())
    vectors = list(embeddings.values())

    max_similarity = -1
    most_similar_pair = (None, None)

    for i in range(len(phrases)):
        for j in range(i + 1, len(phrases)):
            vec1 = np.array(vectors[i])
            vec2 = np.array(vectors[j])

            vec1_norm = vec1 / np.linalg.norm(vec1)
            vec2_norm = vec2 / np.linalg.norm(vec2)

            similarity = np.dot(vec1_norm, vec2_norm)

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_pair = (phrases[i], phrases[j])

    return most_similar_pair

    return "The most similar pair can be found using the cosine similarity calculation between the embedding vectors."


def vector_databases():
    return ""


def function_calling():
    return ""


def get_an_llm_to_say_yes():
    return ""


def import_html_to_google_sheets():
    return ""


def scrape_imdb_movies():
    return ""


def wikipedia_outline():
    return ""


def scrape_the_bbc_weather_api(city):
    location_url = 'https://locator-service.api.bbci.co.uk/locations?' + urlencode({
        'api_key': 'AGbFAKx58hyjQScCXIYrxuEwJh2W2cmv',
        's': city,
        'stack': 'aws',
        'locale': 'en',
        'filter': 'international',
        'place-types': 'settlement,airport,district',
        'order': 'importance',
        'a': 'true',
        'format': 'json'
    })

    result = requests.get(location_url).json()
    
    try:
        location_id = result['response']['results']['results'][0]['id']
    except (KeyError, IndexError):
        raise ValueError(f"No location data found for city: {city}")

    weather_url = f'https://www.bbc.com/weather/{location_id}'

    response = requests.get(weather_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch weather data for {city}. Status code: {response.status_code}")

    soup = BeautifulSoup(response.content, 'html.parser')
    daily_summary = soup.find('div', attrs={'class': 'wr-day-summary'})
    if not daily_summary:
        raise ValueError(f"Weather summary not found on page for {city}")

    daily_summary_list = re.findall('[a-zA-Z][^A-Z]*', daily_summary.text)
    if not daily_summary_list:
        raise ValueError(f"No weather descriptions extracted for {city}")

    datelist = pd.date_range(datetime.today(), periods=len(daily_summary_list)).tolist()
    datelist = [date.date().strftime('%Y-%m-%d') for date in datelist]

    weather_data = {date: desc for date, desc in zip(datelist, daily_summary_list)}

    return json.dumps(weather_data, indent=4)


def find_the_bounding_box_of_a_city():
    return ""


def search_hacker_news(query, points):
    """
    Search Hacker News for the latest post mentioning a specified topic with a minimum number of points.
    
    Args:
        query (str): The topic to search for (e.g., "python").
        points (int): The minimum number of points the post must have.
    
    Returns:
        str: A JSON string containing the link to the latest qualifying post or an error message.
    """
    feed_url = f"https://hnrss.org/newest?q={query}&points={points}"
    feed = feedparser.parse(feed_url)

    if feed.entries:
        latest_post_link = feed.entries[0].link
        result = {"answer": latest_post_link}
    else:
        result = {"answer": "No posts found matching the criteria."}

    return json.dumps(result)


def find_newest_github_user(location, followers, operator):
    """
    Find the newest GitHub user in a specified location with a follower count based on the given operator.
    
    Args:
        location (str): The city to search for (e.g., "Delhi").
        followers (int): The number of followers to filter by.
        operator (str): Comparison operator for followers ("gt" for >, "lt" for <, "eq" for =).
    
    Returns:
        str: The ISO 8601 creation date of the newest valid user, or an error message.
    """
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}

    operator_map = {"gt": ">", "lt": "<", "eq": ""}
    if operator not in operator_map:
        return f"Invalid operator: {operator}. Use 'gt', 'lt', or 'eq'."
    follower_query = f"followers:{operator_map[operator]}{followers}"

    url = f"https://api.github.com/search/users?q=location:{location}+{follower_query}&sort=joined&order=desc"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.json().get('message')}"

    users = response.json().get('items', [])
    if not users:
        return f"No users found in {location} with {follower_query}."

    cutoff_datetime = datetime.datetime(2025, 3, 23, 15, 57, 3, tzinfo=datetime.timezone(datetime.timedelta(hours=-7)))
    cutoff_utc = cutoff_datetime.astimezone(datetime.timezone.utc)

    for user in users:
        user_url = user['url']
        user_response = requests.get(user_url, headers=headers)

        if user_response.status_code == 200:
            user_data = user_response.json()
            created_at = user_data['created_at']  # ISO 8601 format (e.g., "2023-05-10T12:34:56Z")
            created_at_date = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))

            if created_at_date <= cutoff_utc:
                return created_at  
        else:
            print(f"Error fetching user details: {user_response.status_code}")

    return "No valid users found before cutoff date."


def create_a_scheduled_github_action():
    return ""


def extract_tables_from_pdf():
    return ""


def convert_a_pdf_to_markdown():
    return ""


def clean_up_excel_sales_data():
    return ""


def parse_log_line(line):
    # Regex for parsing log lines
    log_pattern = r'^(\S+) (\S+) (\S+) \[(.*?)\] "(\S+) (.*?) (\S+)" (\d+) (\S+) "(.*?)" "(.*?)" (\S+) (\S+)$'
    match = re.match(log_pattern, line)
    if match:
        return {
            "ip": match.group(1),
            "time": match.group(4),  # e.g. 01/May/2024:00:00:00 -0500
            "method": match.group(5),
            "url": match.group(6),
            "protocol": match.group(7),
            "status": int(match.group(8)),
            "size": int(match.group(9)) if match.group(9).isdigit() else 0,
            "referer": match.group(10),
            "user_agent": match.group(11),
            "vhost": match.group(12),
            "server": match.group(13),
        }
    return None


def load_logs(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return pd.DataFrame()

    parsed_logs = []
    # Open with errors='ignore' for problematic lines
    with gzip.open(file_path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            parsed_entry = parse_log_line(line)
            if parsed_entry:
                parsed_logs.append(parsed_entry)
    return pd.DataFrame(parsed_logs)


def convert_time(timestamp):
    return datetime.strptime(timestamp, "%d/%b/%Y:%H:%M:%S %z")


def apache_log_downloads(
    file_path="s-anand.net-May-2024.gz",
    section_prefix="/",
    weekday=0,
    start_hour=0,
    end_hour=24,
    month=1,
    year=2020,
):
    """
    Analyzes the logs to count the number of successful GET requests.

    Parameters:
    - file_path: path to the GZipped log file.
    - section_prefix: URL prefix to filter (e.g., "/telugu/" or "/tamilmp3/").
    - weekday: integer (0=Monday, ..., 6=Sunday).
    - start_hour: start time (inclusive) in 24-hour format.
    - end_hour: end time (exclusive) in 24-hour format.
    - month: integer month (e.g., 5 for May).
    - year: integer year (e.g., 2024).

    Returns:
    - Count of successful GET requests matching the criteria.
    """
    try:
        df = load_logs(file_path)
        if df.empty:
            print("No log data available for processing.")
            return 0

        # Convert time field to datetime
        df["datetime"] = df["time"].apply(convert_time)

        # Filter for the specific month and year
        df = df[(df["datetime"].dt.month == month) & (df["datetime"].dt.year == year)]

        # Filter for the specific day of the week
        df = df[df["datetime"].dt.weekday == weekday]

        # Filter for the specific time window
        df = df[
            (df["datetime"].dt.hour >= start_hour) & (df["datetime"].dt.hour < end_hour)
        ]

        # Apply filters for GET requests, URL prefix, and successful status codes
        filtered_df = df[
            (df["method"] == "GET")
            & (df["url"].str.startswith(section_prefix))
            & (df["status"].between(200, 299))
        ]

        return filtered_df.shape[0]
    except Exception as e:
        return f"Error: {e}"


def apache_log_requests():
    return ""


def clean_up_student_marks():
    return ""


def clean_up_sales_data():
    return ""


def parse_partial_json(
    file_path="q-parse-partial-json.jsonl",
    key="sales",
    num_rows=100,
    regex_pattern=None,
):
    """
    Aggregates the numeric values of a specified key from a JSONL file.

    Parameters:
      file_path (str): The path to the JSONL file.
      key (str): The JSON key whose numeric values will be summed.
      num_rows (int): Expected number of rows.
      regex_pattern (str): A custom regex pattern. If None, a default for the key is used.

    Returns:
      total (float): The aggregated sum of the numeric values. Type casting it to int at the end.
    """
    total = 0
    valid_rows = 0
    error_rows = 0

    # Create a regex pattern to extract the numeric value.
    # If no custom pattern is provided, we assume the JSON line contains something like "key": some_number.
    if regex_pattern is None:
        pattern = re.compile(r'"{}"\s*:\s*([\d\.]+)'.format(re.escape(key)))
    else:
        pattern = re.compile(regex_pattern)

    try:
        with open(file_path, "r") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()
                if not line:
                    continue

                match = pattern.search(line)
                if match:
                    try:
                        # Convert the captured value to float and add to total.
                        value = float(match.group(1))
                        total += value
                        valid_rows += 1
                    except ValueError as ve:
                        print(
                            f"Line {line_number}: Cannot convert value to float. Error: {ve}"
                        )
                        error_rows += 1
                else:
                    print(f"Line {line_number}: No match found for key '{key}'.")
                    error_rows += 1
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Unexpected error while processing the file: {e}"

    # Optionally, you might want to log a warning if the number of valid rows isn't as expected.
    if valid_rows != num_rows:
        return (
            f"Warning: Expected {num_rows} rows, but processed {valid_rows} valid rows."
        )

    return int(total)


def extract_nested_json_keys():
    return ""


def duckdb_social_media_interactions():
    return ""


def transcribe_a_youtube_video():
    return ""


def reconstruct_an_image():
    return ""


functions_dict = {
    "vs_code_version": vs_code_version,
    "make_http_requests_with_uv": make_http_requests_with_uv,
    "run_command_with_npx": run_command_with_npx,
    "use_google_sheets": use_google_sheets,
    "use_excel": use_excel,
    "use_devtools": use_devtools,
    "count_wednesdays": count_wednesdays,
    "extract_csv_from_a_zip": extract_csv_from_a_zip,
    "use_json": use_json,
    "multi_cursor_edits_to_convert_to_json": multi_cursor_edits_to_convert_to_json,
    "css_selectors": css_selectors,
    "process_files_with_different_encodings": process_files_with_different_encodings,
    "use_github": use_github,
    "replace_across_files": replace_across_files,
    "list_files_and_attributes": list_files_and_attributes,
    "move_and_rename_files": move_and_rename_files,
    "compare_files": compare_files,
    "sql_ticket_sales": sql_ticket_sales,
    "write_documentation_in_markdown": write_documentation_in_markdown,
    "compress_an_image": compress_an_image,
    "host_your_portfolio_on_github_pages": host_your_portfolio_on_github_pages,
    "use_google_colab": use_google_colab,
    "use_an_image_library_in_google_colab": use_an_image_library_in_google_colab,
    "deploy_a_python_api_to_vercel": deploy_a_python_api_to_vercel,
    "create_a_github_action": create_a_github_action,
    "push_an_image_to_docker_hub": push_an_image_to_docker_hub,
    "write_a_fastapi_server_to_serve_data": write_a_fastapi_server_to_serve_data,
    "run_a_local_llm_with_llamafile": run_a_local_llm_with_llamafile,
    "llm_sentiment_analysis": llm_sentiment_analysis,
    "llm_token_cost": llm_token_cost,
    "generate_addresses_with_llms": generate_addresses_with_llms,
    "llm_vision": llm_vision,
    "llm_embeddings": llm_embeddings,
    "embedding_similarity": embedding_similarity,
    "vector_databases": vector_databases,
    "function_calling": function_calling,
    "get_an_llm_to_say_yes": get_an_llm_to_say_yes,
    "import_html_to_google_sheets": import_html_to_google_sheets,
    "scrape_imdb_movies": scrape_imdb_movies,
    "wikipedia_outline": wikipedia_outline,
    "scrape_the_bbc_weather_api": scrape_the_bbc_weather_api,
    "find_the_bounding_box_of_a_city": find_the_bounding_box_of_a_city,
    "search_hacker_news": search_hacker_news,
    "find_newest_github_user": find_newest_github_user,
    "create_a_scheduled_github_action": create_a_scheduled_github_action,
    "extract_tables_from_pdf": extract_tables_from_pdf,
    "convert_a_pdf_to_markdown": convert_a_pdf_to_markdown,
    "clean_up_excel_sales_data": clean_up_excel_sales_data,
    "clean_up_student_marks": clean_up_student_marks,
    "apache_log_requests": apache_log_requests,
    "apache_log_downloads": apache_log_downloads,
    "clean_up_sales_data": clean_up_sales_data,
    "parse_partial_json": parse_partial_json,
    "extract_nested_json_keys": extract_nested_json_keys,
    "duckdb_social_media_interactions": duckdb_social_media_interactions,
    "transcribe_a_youtube_video": transcribe_a_youtube_video,
    "reconstruct_an_image": reconstruct_an_image,
}
