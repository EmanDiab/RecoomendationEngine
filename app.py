# Adjusting the real project


import mysql.connector
from mysql.connector import Error
import pandas as pd
import requests
import pickle
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import datetime
import json
import flask
from flask import request, jsonify
import ast

# ===================== Flask app ===============================

app = flask.Flask(__name__)
app.config["DEBUG"] = False


# ==================== Functions ===============================

def string_list(Str):
    return ast.literal_eval(Str)[0]


def strin_to_dict(Str):
    return json.loads(Str)


def ara(Str):
    return Str['ar']


def eng(Str):
    return Str['en']


def lower(Str):
    return Str.lower()


def get_main_category(ID):
    return table[table['id'] == ID]['main_category_id'].values[0]


# ================= My SQL Connection ==========================

try:
    connection = mysql.connector.connect(host=HOST,
                                         database=DATABASE,
                                         user=USER,
                                         password=PASSWORD)
    if connection.is_connected():
        db_Info = connection.get_server_info()
        print("Connected to MySQL Server version ", db_Info)
        cursor = connection.cursor()
        table = pd.read_sql('select id , title , status ,main_category_id,category_id,slug,images,deleted_at  from products;',
                            connection)
        cursor.execute("select database();")
        record = cursor.fetchone()
        print("You're connected to database: ", record)

except Error as e:
    print("Error while connecting to MySQL", e)
finally:
    if (connection.is_connected()):
        cursor.close()
        connection.close()
        print("MySQL connection is closed")

# ============== Preprocessing ================================
table['images'] = table['images'].apply(string_list)
table['title_'] = table['title'].apply(strin_to_dict)
table['title_'] = table['title_'].apply(eng)
table['title_'] = table['title_'].apply(lower)

table = table[table['deleted_at'].isnull()]
table = table[table['status'] == 'active']
table.reset_index(inplace=True)
product_id = list(table['id'])
# ============== content based cosine ===============
tf = TfidfVectorizer(analyzer='word', ngram_range=(1, 3), min_df=0, stop_words='english', lowercase=True)
tfidf_matrix = tf.fit_transform(table['title_'])

cosine_similarities = linear_kernel(tfidf_matrix, tfidf_matrix)
results = {}
for idx, row in table.iterrows():
    # sorting them descently and finding their indexes
    # 100 based on what?!
    similar_indices = cosine_similarities[idx].argsort()[:-100:-1]
    similar_items = [(cosine_similarities[idx][i], table['id'][i]) for i in similar_indices]
    results[row['id']] = similar_items[1:]


# ============== recommender functions =======================
def recommend_one(item_id, num):
    main = get_main_category(item_id)
    medicines = table[table['main_category_id'] == 4]['id'].tolist()
    if main == 4:
        # means it's medicine so recommend just medicine
        allowed_recommend = [(x, y) for x, y in results[item_id] if y in medicines]
    else:
        allowed_recommend = [(x, y) for x, y in results[item_id] if y not in medicines]

    recs = allowed_recommend
    recc = []
    # brand = item(item_id).split(" ")[0].lower()
    for rec in recs:
        recc.append(rec[1])
    return recc


def recommend(item_id, num):
    recs = results[item_id][:num]
    # print(recs)
    recc = []
    brand = item(item_id).split(" ")[0].lower()
    for rec in recs:
        recc.append(int(rec[1]))
        """if brand in name.lower():
            continue
        else:
            recc.append(name) """
    return recc


def item(id):
    return table.loc[table['id'] == id]['title_'].tolist()[0]


def recommend_user(List):
    "input : List of history of products"
    "output : List of recommending products"

    recommendations = []
    if len(List) == 0:
        recommendations1 = recommend(random.choice(product_id), 10)
        recommendations2 = recommend(random.choice(product_id), 10)
        recommendations3 = recommend(random.choice(product_id), 10)
        return recommendations1[-3:] + recommendations2[-3:] + recommendations3[-4:]

    elif len(List) == 1:
        recommendations = recommend_one(List[0], 20)
        return recommendations[-10:]
    elif len(List) == 2:
        recommendations1 = recommend(List[0], 13)
        recommendations2 = recommend(List[1], 13)
        return recommendations1[-5:] + recommendations2[-5:]
    else:
        recommendations1 = recommend(List[0], 10)
        recommendations2 = recommend(List[1], 10)
        recommendations3 = recommend(List[2], 10)
        return recommendations1[-3:] + recommendations2[-3:] + recommendations3[-4:]


# ================ API part ===========================


@app.route('/', methods=['GET'])
def home():
    return '''<h1>Distant Reading Archive</h1>
<p>A prototype API for distant reading of science fiction novels.</p>'''


# A route to return all of the available entries in our catalog.
@app.route('/recommendation', methods=['GET', 'POST'])
def recommendation():
    if 'products' in request.args:
        product_history = request.args.getlist('products', type=int)
        if set(product_history).issubset(set(product_id)):
            pass
            # print(product_history)
            # print(type(product_history[0]))
        else:
            return "Error: One of products is not in our system"
    else:
        return "Error: No products field provided. Please specify an list of products."
    recommendation = recommend_user(product_history)
    recommended_products = []
    for r in recommendation:
        Dic = {}
        Dic['id'] = int(r)
        Dic['product_title'] = strin_to_dict(table[table['id'] == r]['title'].values[0])
        Dic['slug'] = table[table['id'] == r]['slug'].values[0]
        Dic['image'] = table[table['id'] == r]['images'].values[0]
        Dic['main_category_id'] = int(table[table['id'] == r]['main_category_id'].values[0])
        Dic['category_id'] = int(table[table['id'] == r]['category_id'].values[0])
        recommended_products.append(Dic)

    API_Body = {

        "recommended_products": recommended_products
    }
    return jsonify(API_Body)


if __name__ == '__main__':
    app.run()
