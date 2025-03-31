import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from multiprocessing import process
import subprocess
from flask import Flask, request, jsonify
from utils.question_matching import find_similar_question
from utils.file_process import unzip_folder
from utils.function_definations_llm import function_definitions_objects_llm
from utils.openai_api import extract_parameters
from utils.solution_functions import functions_dict
import inspect

app = Flask(__name__)

# Get the absolute path to the data directory
QUESTIONS_FILE = project_root / 'data' / 'questions.json'

tmp_dir = "tmp_uploads"
os.makedirs(tmp_dir, exist_ok=True)

SECRET_PASSWORD = os.getenv("SECRET_PASSWORD")


@app.route("/api/", methods=["POST"])
def process_file():
    question = request.form.get("question")
    file = request.files.get("file")  # Get the uploaded file (optional)
    file_names = []

    # Ensure tmp_dir is always assigned
    tmp_dir = "tmp_uploads"
    try:
        # Use the absolute path for questions.json
        similar_question = find_similar_question(question, str(QUESTIONS_FILE))
        if not similar_question:
            return jsonify({'error': 'No similar question found'}), 404

        if file:
            temp_dir, file_names = unzip_folder(file)
            tmp_dir = temp_dir  # Update tmp_dir if a file is uploaded

        solution_function = functions_dict.get(
            str(similar_question[0]), lambda parameters: "No matching function found"
        )

        # Check if the function requires parameters
        sig = inspect.signature(solution_function)
        if len(sig.parameters) > 0:
            parameters = extract_parameters(
                str(question),
                function_definitions_llm=function_definitions_objects_llm[similar_question[0]],
            )
            if file:
                answer = solution_function(file, *parameters)
            else:
                answer = solution_function(*parameters)
        else:
            # Function doesn't require parameters
            answer = solution_function()

        return jsonify({"answer": answer})
    except Exception as e:
        print(e,"this is the error")
        return jsonify({"error": str(e)}), 500


@app.route('/redeploy', methods=['GET'])
def redeploy():
    password = request.args.get('password')
    print(password)
    print(SECRET_PASSWORD)
    if password != SECRET_PASSWORD:
        return "Unauthorized", 403

    subprocess.run(["../redeploy.sh"], shell=True)
    return "Redeployment triggered!", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
