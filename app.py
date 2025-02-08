from flask import Flask, render_template, request, jsonify
import requests
import google.generativeai as genai
import sqlite3
import os
from datetime import datetime
import logging
import re

app = Flask(__name__)

genai.configure(api_key="AIzaSyBRuD5dvIrCBTDllqGo5mOy_bg4uMBRA6M")
model = genai.GenerativeModel("gemini-1.5-flash")
model1 = genai.GenerativeModel("gemini-pro")

api_key = '12221dd003c94483a56acc23fa8bcd16'   # spoonacular.com Food API 
pic_api_key = "cRrwsrbQBOv4D1kJIIjnfty8Ecqh7Cq4H3lD2HKyOT3ZD1n0bxMwS1w6" # pic API pexels

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# User Login ---------------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    return render_template("login.html")


# Main Menu ---------------------------------------------------------------------------------
@app.route("/index", methods=["GET", "POST"])
def index():
    return render_template("main_index.html")


# Funtion1: Sport ---------------------------------------------------------------------------

# 🎯 运动计划页面
@app.route('/sport', methods=["GET", "POST"])
def home():
    return render_template('1_sport/index.html')

@app.route('/sport/form', methods=["GET", "POST"])
def form():
    return render_template('1_sport/form.html')

@app.route('/sport/generate_plan', methods=['POST'])
def generate_plan():
    user_data = request.form

    prompt = "Generate a customized workout plan based on these inputs:\n"
    for key, value in user_data.items():
        prompt += f"{key}: {value}\n"

    try:
        response = model1.generate_content(prompt)
        plan = response.text if response.text else "No response received."
    except Exception as e:
        plan = f"Error: {str(e)}"

    return render_template('1_sport/result.html', plan=plan)


# 🤖 机器人客服页面
@app.route('/sport/chatbox', methods=["GET", "POST"])
def chatbox():
    return render_template('1_sport/chatbox.html')

@app.route('/query', methods=["GET", 'POST'])
def query_gemini():
    user_question = request.form.get("question")
    logger.debug(f"Received question: {user_question}")
    
    if not user_question:
        return jsonify({"error": "Please provide a question"})

    try:
        prompt = f"""
        Please provide a detailed answer to the question "{user_question}", including:
        1. Action instructions and key points
        2. Related image descriptions and search keywords
        3. Notes and suggestions
        """

        response = model1.generate_content(prompt)
        formatted_text = format_response(response.text)

        image_keywords = re.findall(r'\*\*Search Keywords: (.*?)\*\*', response.text)

        return jsonify({
            "text": formatted_text,
            "imageKeywords": image_keywords
        })

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/exercise_image', methods=['GET'])
def exercise_image():
    # 从请求参数中获取健身动作名称
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'Missing exercise query parameter'}), 400

    # 构造 Pexels API 的请求参数
    url = 'https://api.pexels.com/v1/search'
    params = {
        'query': query,
        'per_page': 1  # 返回1个结果，你可以根据需求修改返回数量
    }
    headers = {
        'Authorization': pic_api_key  # 使用你提供的 Pexels API key
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # 如果响应状态码不是200，将引发异常
        data = response.json()

        if data.get('photos') and len(data['photos']) > 0:
            photo = data['photos'][0]
            # 返回图片的中等尺寸链接
            return jsonify({
                'imageUrl': photo['src']['medium'],
                'photographer': photo.get('photographer', '')
            })
        else:
            return jsonify({'error': 'No image found for the given query'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# 📌 格式化 AI 响应
def format_response(text):
    paragraphs = text.split("\n\n")
    formatted_sections = []

    for section in paragraphs:
        if section.startswith("# "):  # 处理标题
            section = f"<h2>{section.strip('# ')}</h2>"
        elif section.startswith("* "):  # 处理列表
            items = section.split("\n* ")
            formatted_items = ['<li>' + item.strip('* ') + '</li>' for item in items if item]
            section = '<ul>' + ''.join(formatted_items) + '</ul>'
        else:
            section = f"<p>{section}</p >"
        
        formatted_sections.append(section)

    return ''.join(formatted_sections)



# Function2: Diet ---------------------------------------------------------------------------

def get_food_id(food_name):
    url = f"https://api.spoonacular.com/food/ingredients/search"
    params = {
        "query": food_name,
        "number": 1,  # return only 1 result
        "apiKey": api_key
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "results" in data and data["results"]:
        return data["results"][0]["id"]   # return the first result
    else:
        return None
    
def get_food_nutrition(food_id):
    url = f"https://api.spoonacular.com/food/ingredients/{food_id}/information"
    params = {
        "unit": "g",
        "amount": 100,  # 100g 
        "apiKey": api_key
    }
    response = requests.get(url, params=params)
    data = response.json()

    required_nutrients = {"Calories", "Carbohydrates", "Protein", "Fat", "Fiber"}
    nutrition_data = {}

    if "nutrition" in data:
        for nutrient in data["nutrition"]["nutrients"]:
            if nutrient["name"] in required_nutrients:
                nutrition_data[nutrient["name"]] = f"{nutrient['amount']} {nutrient['unit']}"
        return nutrition_data
    else:
        return None

def get_recipe_id(query, number=10):
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "query": query,  # search by key word
        "number": number,  # number of recipes returned
        "apiKey": api_key
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "results" in data and data["results"]:
        return [(recipe["id"], recipe["title"]) for recipe in data["results"]]
    else:
        return None

def get_recipe_details(recipe_id):
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    params = {
        "includeNutrition": True,  # 是否包含营养信息
        "apiKey": api_key
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "title" in data:
        title = data["title"]
        image = data["image"]
        ingredients = [f"{i['amount']} {i['unit']} {i['name']}" for i in data["extendedIngredients"]]
        instructions = data["instructions"] or "No detailed guide"

        nutrition = {}
        if "nutrition" in data:
            for nutrient in data["nutrition"]["nutrients"]:
                if nutrient["name"] in {"Calories", "Protein", "Fat", "Carbohydrates"}:
                    nutrition[nutrient["name"]] = f"{nutrient['amount']} {nutrient['unit']}"

        return {
            "title": title,
            "image": image,
            "ingredients": ingredients,
            "instructions": instructions,
            "nutrition": nutrition
        }
    else:
        return None

def format_recipe_details(recipe_details):
    """格式化食谱详情为可读文本"""
    if not recipe_details:
        return "Recipe not found"
    
    formatted_text = f"\n🍽️ {recipe_details['title']} 🍽️\n"
    formatted_text += f"📷 Picture: {recipe_details['image']}\n\n"
    
    formatted_text += "🥕 Ingredients:\n"
    for ing in recipe_details["ingredients"]:
        formatted_text += f"- {ing}\n"

    formatted_text += "\n📜 Instructions:\n"
    formatted_text += f"{recipe_details['instructions']}\n"

    formatted_text += "\n🔢 Nutrition:\n"
    formatted_text += "Nutrition for every 100g:\n"
    for key, value in recipe_details["nutrition"].items():
        formatted_text += f"- {key}: {value}\n"

    return formatted_text



### Function2.1: Meal PLanning 
@app.route("/diet", methods=["GET", "POST"])
def diet():
    return render_template("2_diet/diet_index.html")

@app.route("/diet/meal", methods=["GET", "POST"])
def meal():
    return render_template("2_diet/meal.html")

@app.route("/diet/meal_plan", methods=["POST"])
def meal_plan():
    goal = request.form.get("goal")  # 获取用户目标（增肌/减脂）
    preferences = request.form.get("preferences")  # 获取食材偏好

    # 构造提示词
    prompt = f"""
    My goal is: {goal}.
    My ingredient preferences are: {preferences}.
    Please generate a diet plan similar to Mint Health that contains:
    1. total calories (kcal) and nutrient ratios (protein, fat, carbohydrates).
    2. detailed recommendations for three meals (food + grams).
    3. an option to change foods.

    The format is as follows:
    ```
    Total calories: 2200 kcal
    Nutritional ratio: Protein 30% (165g), Fat 20% (49g), Carbohydrate 50% (275g).

    Morning (450kcal).
    - Oatmeal 100g
    - 2 poached eggs
    - Soymilk without sugar 200ml

    Lunch (800kcal).
    - Black rice 150g
    - Grilled chicken breast 100g
    - Broccoli 50g

    Dinner (700kcal).
    - Sweet Potato 200g
    - Salmon 120g
    - Avocado 50g
    ```
    Please follow the format output strictly! And A few lines between each meal. And it should be daily plan with 7 days a week.
    """

    # 让 Gemini AI 生成饮食计划
    response = model.generate_content(prompt)

    # 解析 AI 生成的文本
    try:
        meal_plan_text = response.candidates[0].content.parts[0].text
    except:
        meal_plan_text = "Unable to generate diet plan, please try again later."

    # 处理 Markdown 加粗
    meal_plan_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", meal_plan_text)

    # 去除多余的空行
    meal_plan_text = re.sub(r"\n\s*\n", "\n", meal_plan_text)

    # 将换行符替换为 <br> 标签
    formatted_meal_plan = meal_plan_text.replace("\n", "<br>")

    # 将 meal_plan_text 格式化以添加合适的空行
    formatted_meal_plan = formatted_meal_plan.replace("<br><br>", "<br>")  # 去除多余的空行
    formatted_meal_plan = formatted_meal_plan.replace("Option to change foods:", "<br><br>Option to change foods:")  # 增加空行
    formatted_meal_plan = formatted_meal_plan.replace("Important Considerations:", "<br><br>Important Considerations:")  # 增加空行

    return render_template("2_diet/meal_plan.html", meal_plan=formatted_meal_plan)



### Function2.2: Food Search
@app.route("/diet/food", methods=["GET", "POST"])
def food():
    return render_template("2_diet/food.html")

@app.route("/diet/food_result", methods=["GET", "POST"])
def food_result():
    food_name = request.form.get("q")
    food_id = get_food_id(food_name)
    if food_id:
        nutrition_info = get_food_nutrition(food_id)
        print(f"{food_name} nutrition component (every 100g):")
        r = '\n'.join(f"{key}: {value}" for key, value in nutrition_info.items())
        return render_template("2_diet/food_result.html",r=r)
    else:
        r = "There is no such food."
        return render_template("2_diet/food_result.html",r=r)
    
### Function2.3: Recipe Search
@app.route("/diet/recipe", methods=["GET", "POST"])
def recipe():
    return render_template("2_diet/recipe.html")

@app.route("/diet/recipe_result", methods=["GET", "POST"])
def recipe_result():
    recipe_name = request.form.get("q")
    recipes = get_recipe_id(recipe_name) 
    if recipes:
        return render_template("2_diet/recipe_result.html", recipes=recipes)  
    else:
        return render_template("2_diet/recipe_result.html", recipes=[])  

@app.route("/diet/recipe_detail/<int:recipe_id>")
def recipe_detail(recipe_id):
    recipe_info = get_recipe_details(recipe_id)
    if recipe_info:
        formatted_recipe = format_recipe_details(recipe_info)
        return render_template("2_diet/recipe_detail.html", recipe=recipe_info, formatted_recipe=formatted_recipe)
    else:
        return "Recipe not found", 404



# Function3: Health -------------------------------------------------------------------------
# Initialize the SQLite database
def init_db():
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weight_history (
            id INTEGER PRIMARY KEY, 
            date TEXT, 
            weight REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercise_data (
            id INTEGER PRIMARY KEY, 
            date TEXT, 
            heart_rate INTEGER, 
            steps INTEGER, 
            calories INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_data (
            id INTEGER PRIMARY KEY, 
            date TEXT, 
            food_list TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Home - Health management main interface
@app.route("/health", methods=["GET", "POST"])
def health():
    return render_template("3_health/index.html")

# ========= Weight Update & BMI Calculation =========

# Display the weight update form page
@app.route("/health/update_weight_form", methods=["GET", "POST"])
def update_weight_form():
    return render_template("3_health/update_weight.html")

# Handle weight update submission
@app.route("/health/update_weight", methods=["GET", "POST"])
def update_weight():
    weight = request.form.get("weight")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO weight_history (date, weight) VALUES (?, ?)", (date, weight))
    conn.commit()
    conn.close()

    return render_template("3_health/dashboard.html", message="Weight data updated!")

# ========= Sports data submission =========

# Display the sports data form page
@app.route("/health/submit_exercise_form", methods=["GET", "POST"])
def submit_exercise_form():
    return render_template("3_health/submit_exercise.html")

# Processing motion data submission
@app.route("/health/submit_exercise", methods=["GET", "POST"])
def submit_exercise():
    heart_rate = request.form.get("heart_rate")
    steps = request.form.get("steps")
    calories = request.form.get("calories")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO exercise_data (date, heart_rate, steps, calories) VALUES (?, ?, ?, ?)", 
                   (date, heart_rate, steps, calories))
    conn.commit()
    conn.close()

    return render_template("3_health/dashboard.html", message="Sports data recorded!")

# ========= Diet data submission =========

# Display the diet data form page
@app.route("/health/submit_food_form", methods=["GET", "POST"])
def submit_food_form():
    return render_template("3_health/submit_food.html")

# Process dietary data submission & call genAI to calculate calories
@app.route("/health/submit_food", methods=["GET", "POST"])
def submit_food():
    food_list = request.form.get("food_list")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save to database
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO food_data (date, food_list) VALUES (?, ?)", (date, food_list))
    conn.commit()
    conn.close()

    # Call Gemini to calculate 
    prompt = f"Calculate the total calories and nutritional ratio (carbohydrate/protein/fat) of the following foods: {food_list}"
    
    response = model.generate_content(prompt)
    
    nutrition_result = response.text if response and response.text else "Unable to obtain nutritional analysis results"

    return render_template("3_health/dashboard.html", message="Diet data recorded!", nutrition_analysis=nutrition_result)

# ========= Generate health report ==========

@app.route("/health/generate_report", methods=["GET", "POST"])
def generate_report():
    conn = sqlite3.connect("health.db")
    cursor = conn.cursor()

    # Get the weight data for the last 7 days
    cursor.execute("SELECT date, weight FROM weight_history ORDER BY date DESC LIMIT 7")
    weight_history = cursor.fetchall()

    # Get the last 7 days of exercise data
    cursor.execute("SELECT date, heart_rate, steps, calories FROM exercise_data ORDER BY date DESC LIMIT 7")
    exercise_data = cursor.fetchall()

    conn.close()

    # Generate AI health recommendations (based on historical data)
    prompt = f"User's weight change in the last 7 days: {weight_history}, Sports data: {exercise_data}. Please provide an overall health analysis, including weight trends, exercise recommendations, and dietary modification plans."
    response = model.generate_content(prompt)
    
    health_advice = response.text if response and response.text else "Unable to obtain nutritional analysis results"

    return render_template("3_health/health_report.html", 
                           weight_history=weight_history, 
                           exercise_data=exercise_data,
                           health_advice=health_advice)
    





if __name__ == "__main__":
    app.run(debug=True)     


