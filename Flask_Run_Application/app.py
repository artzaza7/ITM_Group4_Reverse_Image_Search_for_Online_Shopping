from werkzeug.utils import secure_filename
import json
import pandas as pd
from scipy.spatial import distance
from PIL import Image
from tensorflow import keras
import tensorflow_hub as hub
import tensorflow as tf
import numpy as np
import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql

app = Flask(__name__)
app.secret_key = 'itm_group_4'
# connection Database

# model library
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


def openConnection():
    connection = pymysql.connect(host='localhost',
                                 user='root',
                                 password='',
                                 database='itm_database',  # Name of database
                                 charset='utf8',
                                 #  cursorclass=pymysql.cursors.DictCursor
                                 )
    return connection


# localhost, username, password, database
# =======================================================
# Model
model = keras.models.load_model(
    'D:/ITM_Group4_Reverse_Image_Search_for_Online_Shopping/Model/preweight/efficientnet.h5', custom_objects={'KerasLayer': hub.KerasLayer})
model.summary()


def extract(file):
    IMAGE_SHAPE = (224, 224)
    file = Image.open(file).convert('L').resize(IMAGE_SHAPE)
    file = np.stack((file,)*3, axis=-1)
    file = np.array(file)/255.0
    embedding = model.predict(file[np.newaxis, ...])
    vgg16_feature_np = np.array(embedding)
    flattended_feature = vgg16_feature_np.flatten()
    return flattended_feature


def searchVector(vector):
    con = openConnection()
    cur = con.cursor()
    cur.execute("Select * From product")
    rows = cur.fetchall()
    data = {
        "id": [],  # row[0]
        "distance": []  # row[4] = vector
    }
    df = pd.DataFrame(data)
    metric = 'cosine'
    for row in rows:
        r = np.array(json.loads(row[4]))
        print(type(r))
        dc = distance.cdist([vector], [r], metric)[0]
        df.loc[len(df.index)] = [row[0], dc]
    return df.sort_values(by=['distance'])

# =======================================================
# =======================================================
# Without User Login


@app.route("/")
def indexWithoutUser():
    return render_template('index.html')


@app.route("/shopping")
def shoppingWithoutUser():
    conn = openConnection()
    cur = conn.cursor()
    sql = "SELECT * FROM `product` NATURAL JOIN product_category"
    cur.execute(sql)
    result_product = cur.fetchall()
    conn.close()
    return render_template('pageWithoutUser/shop.html', product=result_product)


@app.route("/search")
def searchWithoutUser():
    return render_template('pageWithoutUser/search.html')


@app.route("/sign_in")
def signInPage():
    return render_template('pageWithoutUser/signin.html')


@app.route("/sign_up")
def signUpPage():
    return render_template('pageWithoutUser/signup.html')


@app.route("/aboutUs")
def aboutUsPage():
    return render_template('pageWithoutUser/aboutUs.html')

# @app.route("/resultSearch")
# def resultSearchPage():
#     return render_template('pageWithoutUser/resultSearch.html')

# =======================================================

# action

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('signInPage'))


@app.route("/sign_in/actions", methods=['POST'])
def signInLogin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = openConnection()
        cur = conn.cursor()
        # hashed_password = generate_password_hash(password, method='sha256')
        # print(hashed_password)
        # sql = "SELECT * FROM `user` NATURAL JOIN `user_type` WHERE user.user_email = %s AND user.user_password = %s"
        sql = "SELECT * FROM `user` NATURAL JOIN `user_type` WHERE user.user_email = %s"
        cur.execute(sql, (email))
        result = cur.fetchone()

        userType = result[6]
        conn.close()
        if result and check_password_hash(result[5], password):
            # if result :
            session['user'] = result[1]
            if userType == "ADMIN":
                return redirect(url_for('adminPageUser', userType_name=result[6], user_id=result[1]))
            elif (userType == "USER"):
                return redirect(url_for('userPageShopping', userType_name=result[6], user_id=result[1]))
        else:
            return redirect(url_for('signInPage'))
    else:
        return redirect(url_for('signInPage'))


@app.route("/sign_up/actions", methods=['POST'])
def signUpLogin():
    firstname = request.form['firstname']
    lastname = request.form['lastname']
    email = request.form['email']
    password = request.form['password']
    user = 2
    hashed_password = generate_password_hash(password, method='sha256')
    conn = openConnection()
    cur = conn.cursor()
    sql = "INSERT INTO `user`(`user_email`, `user_fname`, `user_lname`, `user_password`, `userType_id`) VALUES (%s, %s, %s, %s, %s)"
    cur.execute(sql, (email, firstname, lastname, hashed_password, user))
    conn.commit()
    conn.close()
    # INSERT INTO `user`(`user_id`, `user_email`, `user_fname`, `user_lname`, `user_password`, `userType_id`) VALUES ('[value-1]','[value-2]','[value-3]','[value-4]','[value-5]','[value-6]')
    return redirect(url_for('signInPage'))

# action adding product


@app.route("/<string:userType_name>/<string:user_id>/insert_product", methods=['POST'])
def adminPageActionAddingProduct(userType_name, user_id):
    if request.method == "POST":
        product_name = request.form['product_name']
        product_color = request.form['product_color']
        product_cost = request.form['product_cost']
        product_category = request.form['product_category']
        file_image = request.files['product_image']
        filename = secure_filename(product_name+".jpg")

        # path folder for save img for upload
        file_image.save(
            'D:/ITM_Group4_Reverse_Image_Search_for_Online_Shopping/Flask_Run_Application/static/img_product_into_db/' + filename)

        # path folder for save img for call img into database with feature
        folder_path = "D:/ITM_Group4_Reverse_Image_Search_for_Online_Shopping/Flask_Run_Application/static/img_product_into_db/{}".format(
            filename)
        feature = extract(folder_path)
        js = json.dumps(feature.tolist())
        product_vector = js

        con = openConnection()
        cur = con.cursor()
        sql = "INSERT INTO `product` (`product_name`, `product_img_name`, `product_cost`, `product_vector`, `product_color`, `productCategory_id`) VALUES (%s, %s, %s, %s, %s, %s)"
        cur.execute(sql, (product_name, filename, product_cost,
                    product_vector, product_color, product_category))
        con.commit()
        con.close()

        return redirect(url_for('adminPageProduct', userType_name=userType_name, user_id=user_id))

@app.route('/search', methods=['POST'])
def searchAction():
    file = request.files['fileUpload']
    filename = secure_filename("search.jpg")
    file.save('D:/ITM_Group4_Reverse_Image_Search_for_Online_Shopping/Flask_Run_Application/static/search_upload/'+ filename)
    folder_path = "D:/ITM_Group4_Reverse_Image_Search_for_Online_Shopping/Flask_Run_Application/static/search_upload/{}".format(filename)
    df = searchVector(extract(folder_path))
    id = df['id'].values.tolist()
    result = np.empty((0, 8))
    con = openConnection()
    cur = con.cursor()
    sql ="SELECT * FROM `product` NATURAL JOIN product_category WHERE product_id = %s"
    for i in id[:4]: #best of ...
        cur.execute(sql,(i))
        row = cur.fetchall()
        result = np.append(result,np.array(row),axis=0)
    result = tuple(map(tuple, result))
    return render_template('pageWithoutUser/resultSearch.html', datas=result)

@app.route('/<string:userType_name>/<string:user_id>/search', methods=['POST'])
def searchActionWithUser(userType_name, user_id):
    conn = openConnection()
    cur = conn.cursor()
    # sql = "SELECT * FROM `product` NATURAL JOIN product_category"
    sql = "SELECT product_id FROM `product` NATURAL JOIN product_category WHERE product_id IN ( SELECT product_id FROM favoriteproduct WHERE user_id = %s)"
    cur.execute(sql,(user_id))
    result_product = cur.fetchall()
    conn.close()
    # print(result_product)
    # print(type(result_product))
    # for save in result_product : 
    #     print(save)
    file = request.files['fileUpload']
    filename = secure_filename("search.jpg")
    file.save('D:/ITM_Group4_Reverse_Image_Search_for_Online_Shopping/Flask_Run_Application/static/search_upload/'+ filename)
    folder_path = "D:/ITM_Group4_Reverse_Image_Search_for_Online_Shopping/Flask_Run_Application/static/search_upload/{}".format(filename)
    df = searchVector(extract(folder_path))
    id = df['id'].values.tolist()
    # print(id)
    # for result_id in id:
    #     i = 0
    #     while (i< len(result_product)):
    #         print(f"result_id {result_id} | save {result_product[i][0]}")
    #         print(result_product[i][0] == result_id)
    #         i += 1
    result = np.empty((0, 8))
    con = openConnection()
    cur = con.cursor()
    sql ="SELECT * FROM `product` NATURAL JOIN product_category WHERE product_id = %s"
    # AND product_id NOT IN ( SELECT product_id FROM favoriteproduct WHERE user_id = %s)
    for save in id :
        print(save)

    i = 0
    listSave = []
    # cur.execute(sql,(id[i]))
    # row = cur.fetchall()
    # result = np.append(result,np.array(row),axis=0)
    while (i<len(id)): #best of ...
        favorite = False
        saveID = id[i]
        y = 0
        while (y<len(result_product)):
            print(f"result_prduct = {result_product[y][0]} | id = {id[i]}")
            print(result_product[y][0] == id[i])
            if result_product[y][0] == id[i]:
                favorite = True
                saveID = id[i]
            y += 1
        if not favorite : 
            listSave.append(saveID)
        i += 1

    print(listSave)

    for i in listSave[:4]: #best of ...
        cur.execute(sql,(i))
        row = cur.fetchall()
        result = np.append(result,np.array(row),axis=0)
        
    result = tuple(map(tuple, result))
    return render_template('pageWithUser/Userpage/userResultSearch.html', data_userType=userType_name, data_id=user_id, datas=result) 



# =======================================================
# With User Login


@app.route("/<string:userType_name>/<string:user_id>/users")
def adminPageUser(userType_name, user_id):
    if 'user' in session:
        conn = openConnection()
        cur = conn.cursor()
        sql = "SELECT * FROM `user` WHERE user_id != %s"
        cur.execute(sql, (user_id))
        result_user = cur.fetchall()
        conn.close()
        return render_template('pageWithUser/Adminpage/user/user.html', data_user=result_user, data_id=user_id, data_userType=userType_name)
    else:
        return redirect(url_for('signInPage'))


@app.route("/<string:userType_name>/<string:user_id>/products")
def adminPageProduct(userType_name, user_id):

    if 'user' in session:
        conn = openConnection()
        cur = conn.cursor()
        sql = "SELECT * FROM `product` NATURAL JOIN product_category"
        cur.execute(sql)
        result_product = cur.fetchall()
        conn.close()
        return render_template('pageWithUser/Adminpage/product/product.html', data_product=result_product, data_id=user_id, data_userType=userType_name)
    else:
        return redirect(url_for('signInPage'))


@app.route("/<string:userType_name>/<string:user_id>/products/addProduct")
def adminPageAddProduct(userType_name, user_id):
    if 'user' in session:
        con = openConnection()
        cur = con.cursor()
        cur.execute("SELECT * FROM `product_category`")
        product_category_result = cur.fetchall()
        return render_template('pageWithUser/Adminpage/Addproduct/addproduct.html', data_id=user_id, data_userType=userType_name, product_category=product_category_result)
    else:
        return redirect(url_for('signInPage'))


@app.route("/<string:userType_name>/<string:user_id>/shopping")
def userPageShopping(userType_name, user_id):
    if 'user' in session:
        conn = openConnection()
        cur = conn.cursor()
        # sql = "SELECT * FROM `product` NATURAL JOIN product_category"
        sql = "SELECT * FROM `product` NATURAL JOIN product_category WHERE product_id NOT IN ( SELECT product_id FROM favoriteproduct WHERE user_id = %s)"
        cur.execute(sql,(user_id))
        result_product = cur.fetchall()
        conn.close()
        return render_template('pageWithUser/Userpage/user.html', data_id=user_id, data_userType=userType_name, product=result_product)
    else:
        return redirect(url_for('signInPage'))
    
@app.route("/<string:userType_name>/<string:user_id>/search")
def userPageSearch(userType_name, user_id):
    if 'user' in session:
        return render_template('pageWithUser/Userpage/userSearch.html', data_id=user_id, data_userType=userType_name)
    else:
        return redirect(url_for('signInPage'))
    
@app.route("/<string:userType_name>/<string:user_id>/about_us")
def userPageAboutUs(userType_name, user_id):
    if 'user' in session:
        return render_template('pageWithUser/Userpage/userAboutUs.html', data_id=user_id, data_userType=userType_name)
    else:
        return redirect(url_for('signInPage'))
    
@app.route("/<string:userType_name>/<string:user_id>/favorite")
def userPageFavorite(userType_name, user_id):
    if 'user' in session:
        conn = openConnection()
        cur = conn.cursor()
        sql = "SELECT * FROM `product` NATURAL JOIN product_category WHERE product_id IN ( SELECT product_id FROM favoriteproduct WHERE user_id = %s)"
        cur.execute(sql, (user_id))
        result = cur.fetchall()
        conn.close()
        return render_template('pageWithUser/Userpage/userFavorite.html', data_id=user_id, data_userType=userType_name, product = result)
    else:
        return redirect(url_for('signInPage'))
# =======================================================


if __name__ == "__main__":
    app.run(debug=True)
