from flask import Flask, render_template, request
import requests
import google.generativeai as genai

api_key = '12221dd003c94483a56acc23fa8bcd16'

genai.configure(api_key="AIzaSyBRuD5dvIrCBTDllqGo5mOy_bg4uMBRA6M")
model = genai.GenerativeModel("gemini-1.5-flash")

app = Flask(__name__)


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

def get_recipe_id(query, number=5):
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


@app.route("/", methods=["GET", "POST"])
def diet():
    return render_template("diet.html")


@app.route("/meal", methods=["GET", "POST"])
def meal():
    return render_template("meal.html")

@app.route("/meal_plan", methods=["POST"])
def meal_plan():
    goal = request.form.get("goal")  # 获取用户目标（增肌/减脂）
    preferences = request.form.get("preferences")  # 获取食材偏好

    # 构造提示词
    prompt = f"""
    My goal is: {goal}.
    My ingredient preferences are：{preferences}.
    Please generate a diet plan similar to Mint Health that contains:
    1. total calories (kcal) and nutrient ratios (protein, fat, carbohydrates).
    2. detailed recommendations for three meals (food + grams).
    3. an option to change foods.

    The format is as follows:
    ``
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
    、、
    Please follow the format output strictly! And A few lines between each meal. And it should be daily plan with 7 days a week.
    """


    # 让 Gemini AI 生成饮食计划
    response = model.generate_content(prompt)

    # 解析 AI 生成的文本
    try:
        meal_plan_text = response.candidates[0].content.parts[0].text
    except:
        meal_plan_text = "Unable to generate diet plan, please try again later."

    return render_template("meal_plan.html", meal_plan=meal_plan_text)


@app.route("/food", methods=["GET", "POST"])
def food():
    return render_template("food.html")

@app.route("/food_result", methods=["GET", "POST"])
def food_result():
    food_name = request.form.get("q")
    food_id = get_food_id(food_name)
    if food_id:
        nutrition_info = get_food_nutrition(food_id)
        print(f"{food_name} nutrition component (every 100g):")
        r = '\n'.join(f"{key}: {value}" for key, value in nutrition_info.items())
        return render_template("food_result.html",r=r)
    else:
        r = "There is no such food."
        return render_template("food_result.html",r=r)
    

@app.route("/recipe", methods=["GET", "POST"])
def recipe():
    return render_template("recipe.html")

@app.route("/recipe_result", methods=["GET", "POST"])
def recipe_result():
    recipe_name = request.form.get("q")
    recipes = get_recipe_id(recipe_name) 
    if recipes:
        return render_template("recipe_result.html", recipes=recipes)  
    else:
        return render_template("recipe_result.html", recipes=[])  

@app.route("/recipe_detail/<int:recipe_id>")
def recipe_detail(recipe_id):
    recipe_info = get_recipe_details(recipe_id) 
    if recipe_info:
        return render_template("recipe_detail.html", recipe=recipe_info)
    else:
        return "Recipe not found", 404





if __name__ == "__main__":
    app.run(debug=True)     