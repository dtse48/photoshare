import random
import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask_login

#for image uploading
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'YOUR_PASSWORD_HERE'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')

@app.route("/email_exists", methods=['GET'])
def email_exists():
	return render_template('email_exists.html', supress='True')

@app.route("/listfriends", methods=['GET'])
@flask_login.login_required
def listfriends():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT first_name,last_name FROM (SELECT user_id2 FROM Friends WHERE user_id1 = ('{0}')) as Temp, Users WHERE Temp.user_id2 = user_id".format(user_id))
	friends = cursor.fetchall()
	friends = [list(i) for i in friends]
	return render_template('list_friends.html',friends = friends)


# for the form to add a friend
@app.route("/findfriends", methods=['GET'])
@flask_login.login_required
def findfriends():
	return render_template('find_friends.html')

@app.route("/findfriends", methods=['POST'])	
def find_a_friend():
	self_id = getUserIdFromEmail(flask_login.current_user.id)
	#make sure query does not return the user himself
	user_id = request.form.get('user_id')
	cursor = conn.cursor()
	cursor.execute("SELECT first_name,last_name FROM Users WHERE user_id = ('{0}') AND user_id <> ('{1}')".format(user_id,self_id))
	friend = cursor.fetchall()
	cursor.execute("SELECT * FROM Friends WHERE user_id1 = '{0}' AND user_id2 = '{1}'".format(self_id,user_id))
	result = cursor.fetchall()
	if (result):
		return render_template('hello.html',message="You have already added this user as a friend!")
	friend = list(friend)
	no_matches_found = False
	if (friend == []):
		no_matches_found = True
	if (not no_matches_found):
		cursor.execute("INSERT INTO Friends (user_id1,user_id2) VALUES ('{0}','{1}')".format(self_id,user_id))
		conn.commit()
	return render_template('search_for_friend_results.html',friend = friend,no_matches_found = no_matches_found)

@app.route("/register", methods=['POST'])
def register_user():
	try:
		firstName=request.form.get('firstName')
		lastName=request.form.get('lastName')
		email=request.form.get('email')
		password=request.form.get('password')
		DOB=request.form.get('DOB')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		cursor.execute("SELECT user_id FROM Users")
		user_ids = cursor.fetchall()
		user_ids = [list(i) for i in user_ids]
		new_id = random.randint(0,1000)
		while ([new_id] in user_ids):
			new_id = random.randint(0,1000)
		print(cursor.execute("INSERT INTO Users (user_id, email, password, first_name, last_name, birth_date) VALUES ('{0}', '{1}','{2}','{3}','{4}','{5}')".format(new_id,email,password,firstName,lastName,DOB)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT picture, photo_id, caption FROM Photos WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if (request.method == 'POST'):
		uid = getUserIdFromEmail(flask_login.current_user.id)
		original_album_id = request.form.get('album_id')
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		tags = request.form.get('tags')
		tagList = list(set(tags.split(';')))
		photo_data =imgfile.read()
		cursor = conn.cursor()
		cursor.execute(" SELECT (albums_id) FROM Albums WHERE albums_id = ('{0}') ".format(original_album_id))
		album_id = cursor.fetchall()
		message = "Photo uploaded!"


		#cursor.execute('''INSERT INTO Pictures (imgdata, user_id, caption) VALUES (%s, %s, %s )''' ,(photo_data,uid, caption))

		#return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid),base64=base64)


		cursor.execute("SELECT photo_id FROM Photos")
		photo_ids = cursor.fetchall()
		photo_ids = [list(i) for i in photo_ids]
		new_id = random.randint(0,1000)
		while ([new_id] in photo_ids):
			new_id = random.randint(0,1000)
		if (list(album_id) != []):
			cursor.execute("SELECT user_id FROM Albums WHERE albums_id = ('{0}')".format(original_album_id))
			owner_id = list(cursor.fetchall())
			if (owner_id == [(uid,)]):
				cursor.execute("INSERT INTO Photos (photo_id, picture, user_id, caption, albums_id) VALUES (%s, %s, %s, %s, %s)" ,(new_id, photo_data, uid, caption, original_album_id))
				for t in tagList:
					if t == "":
						tagList.remove("")
				for t in tagList:
					cursor.execute("SELECT tag_id FROM Tags")
					tag_ids = cursor.fetchall()
					tag_ids = [list(i) for i in tag_ids]
					newtag_id = random.randint(0,1000)
					while ([newtag_id] in tag_ids):
						newtag_id = random.randint(0,1000)
					cursor.execute('''INSERT INTO Tags (tag_id, tName, picture_id) VALUES (%s, %s, %s)''',(newtag_id, t, new_id))
					conn.commit()
				return render_template('hello.html', name=flask_login.current_user.id, message=message, photos=getUsersPhotos(uid),base64=base64)
			else:
				message = "You do not own this album!"
				return render_template('upload_failed.html',message = message)
		else:
			message = "Album does not exist!"
			return render_template('upload_failed.html',message = message)
		

	#The method is GET so we return a  HTML form to upload the a photo.
	
	return render_template('upload.html')
#end photo uploading code

#default page
@app.route("/", methods=['GET', 'POST'])
def hello():
	try: 
		return render_template('hello.html', message='Welecome to Photoshare', name = flask_login.current_user.id)
	except: 
		return render_template('hello.html', message='Welecome to Photoshare')

@app.route('/listTag/<name>')
@flask_login.login_required
def listTag(name, method=['GET']):
	uid = getUserIdFromEmail(name)
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT tName FROM Photos, Tags WHERE user_id = '{0}' AND Tags.picture_id = Photos.photo_id".format(uid))
	return render_template('listTag.html', tags = cursor.fetchall(), name = name)

@app.route('/showPopularTags')
def showPopularTags(method=['GET']):
	cursor = conn.cursor()
	cursor.execute("SELECT tName, COUNT(tName) FROM Tags GROUP BY tName ORDER BY COUNT(tName) DESC")
	return render_template('showPopularTags.html', tags = cursor.fetchall())

@app.route('/showPhoto/<tag>/<name>')
def showPhoto(tag, name):
	if name != "-1":#search photo's w/ tags that <name> used
		uid = getUserIdFromEmail(name)
		cursor = conn.cursor()
		cursor.execute("SELECT DISTINCT photo_id, picture, tName FROM Photos, Tags, Users WHERE Tags.picture_id = Photos.photo_id AND Photos.user_id = Users.user_id AND Tags.tName = '{0}' AND Photos.user_id = '{1}' AND Users.email = '{2}'".format(tag, uid, name))
		return render_template('showPhoto.html', tag = tag, photoTag = cursor.fetchall(), base64=base64)
	else:
		cursor = conn.cursor()
		cursor.execute("SELECT DISTINCT Photos.photo_id, picture, tName FROM Photos, Tags WHERE Tags.picture_id = Photos.photo_id AND Tags.tName = '{0}'".format(tag))
		return render_template('showPhoto.html', tag = tag, photoTag = cursor.fetchall(), base64=base64)

@app.route('/searchTag', methods=['GET', 'POST'])
def searchTag():
	if request.method == 'GET':
		return render_template('searchTag.html')
	else:
		t = request.form.get('tag')
		return redirect(url_for('showPhoto', tag = t, name = -1))

@app.route('/createalbum', methods=['GET'])
@flask_login.login_required
def createalbum():
	return render_template('create_album.html')

#create album through form
@app.route('/createalbum', methods=['POST'])
@flask_login.login_required
def create_album():
	name = request.form.get('name')
	date = request.form.get('date')
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id FROM Albums")
	ids = cursor.fetchall()
	ids = [list(i) for i in ids]
	new_id = random.randint(0,1000)
	while ([new_id] in ids):
		new_id = random.randint(0,1000)
	cursor.execute("INSERT INTO Albums (albums_id,album_name,date_of_creation,user_id) VALUES ('{0}','{1}','{2}','{3}')".format(new_id,name,date,user_id))	
	conn.commit()
	return render_template('upload.html',message = "Album created with id "+str(new_id) + "!") 
	
@app.route('/deletealbum', methods=['GET'])
@flask_login.login_required
def deletealbum():
	return render_template('delete_album.html')

@app.route('/deletealbum', methods=['POST'])
@flask_login.login_required
def delete_album():
	album_id = request.form.get('album_id')
	cursor = conn.cursor()
	cursor.execute(" SELECT (user_id) FROM Albums WHERE albums_id = ('{0}') ".format(album_id))
	result = cursor.fetchall()
	if (result == ()):
		return render_template('hello.html',message = "This album does not exist!")
	if (int(result[0][0]) != getUserIdFromEmail(flask_login.current_user.id)):
		return render_template('hello.html',message = "You do not own this album!")
	cursor.execute("DELETE FROM Albums WHERE albums_id = ('{0}')".format(album_id))
	conn.commit()
	return render_template('hello.html',message = "Album deleted!")

@app.route('/allalbums',methods = ['GET'])
@flask_login.login_required
def display_albums():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT album_name,albums_id FROM Albums WHERE user_id = ('{0}')".format(user_id))
	albums = cursor.fetchall()	
	return render_template('all_albums.html',albums = albums)

@app.route('/publicallalbums',methods = ['GET'])
def public_display_albums():
	return render_template('all_albums.html')

@app.route('/viewalbum',methods = ['POST'])
def view_album():
	album_id = request.form.get('album_id')
	cursor = conn.cursor()
	cursor.execute("SELECT picture, photo_id, caption FROM Photos WHERE albums_id = '{0}'".format(album_id))
	photos = cursor.fetchall()
	album_name = ""
	if (photos):
		cursor.execute("SELECT album_name FROM Albums WHERE albums_id = '{0}'".format(album_id))
		album_name = cursor.fetchall()[0][0]
		
	return render_template('display_album.html',photos = photos,base64=base64, album_name = album_name)

@app.route('/deletephoto', methods=['GET'])
@flask_login.login_required
def deletephoto():
	return render_template('delete_photo.html')

@app.route('/deletephoto', methods=['POST'])
@flask_login.login_required
def delete_photo():
	album_id = request.form.get('album_id')
	cursor = conn.cursor()
	cursor.execute(" SELECT (user_id) FROM Albums WHERE albums_id = ('{0}') ".format(album_id))
	result = cursor.fetchall()
	if (result == ()):
		return render_template('hello.html',message = "This album does not exist!")
	if (int(result[0][0]) != getUserIdFromEmail(flask_login.current_user.id)):
		return render_template('hello.html',message = "You do not own this album!")
	photo_id = request.form.get('photo_id')
	cursor.execute(" SELECT (photo_id) FROM Photos WHERE photo_id = ('{0}') ".format(photo_id))
	if (cursor.fetchall() == ()):
		return render_template('hello.html',message = "Photo does not exist!")
	cursor.execute("DELETE FROM Photos WHERE photo_id = ('{0}')".format(photo_id))
	conn.commit()
	return render_template('hello.html',message = "Photo deleted!")

@app.route('/listallalbums', methods=['GET'])
def viewallalbums():
	cursor = conn.cursor()
	cursor.execute(" SELECT album_name,albums_id,user_id FROM Albums ")
	albums = cursor.fetchall()
	return render_template('view_all_albums.html',albums = albums)

@app.route('/comment',methods = ['GET'])
def comment():
	return render_template('comment.html')

@app.route('/comment',methods = ['POST'])
def submit_comment():
	photo_id = request.form.get('photo_id')
	comment = request.form.get('comment')
	date = request.form.get('date')
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Photos WHERE photo_id = ('{0}')".format(photo_id))
	owner_id = cursor.fetchall()
	if (not owner_id):
		return render_template('comment_results.html',message = "Photo does not exist!")
	
	cursor.execute("SELECT comment_id FROM Comments")
	all_comment_ids = cursor.fetchall()
	new_id = random.randint(0,1000)
	while ((new_id,) in all_comment_ids):
		new_id = random.randint(0,1000)
	
	if (not flask_login.current_user.is_authenticated):
		cursor.execute("INSERT INTO Comments (comment_id, user_id, photo_id, text, date) VALUES ('{0}',NULL,'{1}','{2}','{3}')".format(new_id,photo_id,comment,date))
		conn.commit()
		return render_template('comment_results.html',message = "Comment added!")
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	if (owner_id[0][0] == user_id):
		return render_template('comment_results.html',message = "You cannot comment on your own photos!")
	
	cursor.execute("INSERT INTO Comments (comment_id, user_id, photo_id, text, date) VALUES ('{0}','{1}','{2}','{3}','{4}')".format(new_id,user_id,photo_id,comment,date))
	conn.commit()
	return render_template('comment_results.html',message = "Comment added!")

@app.route('/viewcomments',methods = ['GET'])
def viewcomments():
	return render_template('view_comments.html')

@app.route('/viewcomments',methods = ['POST'])
def view_comments():
	photo_id = request.form.get('photo_id')
	cursor = conn.cursor()
	cursor.execute("SELECT picture, photo_id, caption FROM Photos WHERE photo_id = '{0}'".format(photo_id))
	photo = cursor.fetchall()
	if (not photo):
		return render_template('comments_results.html',message = "Photo does not exist!")
	cursor.execute("SELECT text FROM Comments WHERE photo_id = ('{0}')".format(photo_id))
	comments = cursor.fetchall()
	return render_template('comments_results.html',photo = photo[0],base64=base64,comments=comments)

@app.route('/like',methods = ['GET'])
def like():
	return render_template('like.html')

@app.route('/like',methods = ['POST'])
def like_photo():
	photo_id = request.form.get('photo_id')
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Photos WHERE photo_id = ('{0}')".format(photo_id))
	result = cursor.fetchall()
	if (not result):
		return render_template('hello.html',message = "Photo does not exist!")
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	cursor.execute("SELECT user_id FROM Likes WHERE photo_id = ('{0}')".format(photo_id))
	result = cursor.fetchall()
	if ((user_id,) in result):
		return render_template('hello.html',message = "You have already liked this photo!") 
	cursor.execute("INSERT INTO Likes (photo_id,user_id) VALUES ('{0}','{1}')".format(photo_id,user_id))
	conn.commit()
	return render_template('hello.html',message = "Like added!")	
	
@app.route('/viewlikes',methods = ['GET'])
def viewlikes():
	return render_template('view_likes.html')

@app.route('/viewlikes',methods = ['POST'])
def view_likes():
	photo_id = request.form.get('photo_id')
	cursor = conn.cursor()
	cursor.execute("SELECT picture, photo_id, caption FROM Photos WHERE photo_id = '{0}'".format(photo_id))
	photo = cursor.fetchall()
	if (not photo):
		return render_template('hello.html',message = "Photo does not exist!")
	cursor.execute("SELECT user_id FROM Likes WHERE photo_id = ('{0}')".format(photo_id))
	likers = cursor.fetchall()
	num_likes = len(likers)
	return render_template('likes_results.html',photo = photo[0],base64=base64,likers=likers,num_likes=num_likes)	

@app.route('/searchcomments',methods = ['GET'])
def searchcomments():
	return render_template('search_comments.html')

@app.route('/searchcomments',methods = ['POST'])
def search_comments():
	comment = request.form.get('comment')
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Comments WHERE text = '{0}'".format(comment))
	users = list(cursor.fetchall())
	if (not users):
		return render_template('hello.html',message="No comments matched your search!")
	final_list = {}
	for user in users:
		user_id = user[0]
		if (user_id == None):
			continue
		cursor.execute("SELECT user_id, comment_id FROM Comments WHERE text = '{0}' AND user_id = '{1}'".format(comment,user_id))
		data = cursor.fetchall()
		final_list[user_id] = len(data)
	final_list = sorted(final_list.items(),key = lambda x:x[1],reverse = True)
	return render_template('search_comments_results.html',final_list = final_list,comment = comment)	

def calculate_score(user_id):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(*) FROM Photos WHERE user_id = '{0}'".format(user_id))
	score = cursor.fetchall()[0][0]
	cursor.execute("SELECT COUNT(*) FROM Comments WHERE user_id = '{0}'".format(user_id))
	score += cursor.fetchall()[0][0]
	return score

def getTopScores():
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Users")
	users = cursor.fetchall()
	print(users)
	scores = {}
	for user in users:
		score = calculate_score(user[0])
		scores[user[0]] = score
	scores = sorted(scores.items(),key = lambda x:x[1],reverse=True)
	if (len(scores) >= 10):
		return scores[0:10]
	return scores


@app.route('/topusers',methods = ['GET'])
def topusers():
	top_users = getTopScores()
	return render_template('top_users.html',top_users = top_users)

@app.route('/showid',methods = ['GET'])
@flask_login.login_required
def showid():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('user_id.html',id = user_id)

def recommendFriends(user_id):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id2 FROM Friends WHERE user_id1 = '{0}'".format(user_id))
	friends = cursor.fetchall()
	recs = {}
	print(friends)
	for friend in friends: 
		cursor.execute("SELECT user_id2 FROM Friends WHERE user_id1 = '{0}' AND user_id2 <> '{1}'".format(friend[0],user_id))
		friends_of_friend = cursor.fetchall()
		for friend2 in friends_of_friend:
			if (friend2[0] in recs):
				recs[friend2[0]] += 1
			else:
				recs[friend2[0]] = 1
	recs = sorted(recs.items(),key = lambda x:x[1],reverse=True)
	return recs

@app.route('/recommendfriends',methods=['GET'])
@flask_login.login_required
def rec_friends():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	recs = recommendFriends(user_id)
	return render_template('friendrec.html',recs=recs)

@app.route('/recommendPhotos', methods=['GET'])
@flask_login.login_required
def recommendPhoto():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	countTopTags = {}
	countTags = {}
	topFiveTags = []
	
	cursor = conn.cursor()

	tag5 = {}
	tag4 = {}
	tag3 = {}
	tag2 = {}
	tag1 = {}

	#gets top 5 tags
	cursor.execute("SELECT tName, COUNT(*) FROM Tags, Photos WHERE Tags.picture_id = Photos.photo_id AND Photos.user_id = '{0}' GROUP BY tName ORDER BY COUNT(tName) DESC LIMIT 5".format(user_id))
	tags = cursor.fetchall()

	for tag in tags:
		topFiveTags.append(tag[0])

	#get all photos not by user in db 
	cursor.execute("SELECT Photos.photo_id, Photos.picture, Tags.tName FROM Photos, Tags WHERE Photos.photo_id = Tags.picture_id AND Photos.user_id <> '{0}'".format(user_id))
	photos = cursor.fetchall()

	for photo in photos:
		pID = photo[0]
		pic = photo[1]
		pTag = photo[2]

		#count tags in each photo
		if (pID, pic) in countTags:
			countTags[(pID, pic)] = countTags[(pID, pic)] + 1
		else:
			countTags[(pID, pic)] = 1 

		#counts tags in top 5 tags 0-5
		if pTag in topFiveTags:
			if (pID, pic) in countTopTags:
				countTopTags[(pID, pic)] = countTopTags[(pID, pic)] + 1
			else:
				countTopTags[(pID, pic)] = 1 

	for key in countTopTags:
		if countTopTags[key] == 5:
			tag5[key] = int((countTopTags[key] / countTags[key])*100)
			#print(tag5[key])
		elif countTopTags[key] == 4:
			tag4[key] = int((countTopTags[key] / countTags[key])*100)
			#print(tag4[key])
		elif countTopTags[key] == 3:
			tag3[key] = int((countTopTags[key] / countTags[key])*100) 
			#print(tag3[key])
		elif countTopTags[key] == 2:
			tag2[key] = int((countTopTags[key] / countTags[key])*100)  
			#print(tag2[key])
		elif countTopTags[key] == 1:
			tag1[key] = int((countTopTags[key] / countTags[key])*100)  
			#print(tag1[key])
	
	final = []
	five = sorted(tag5.items(), key=lambda x: x[1], reverse=True)
	for x in five:
		final.append(x)
	four = sorted(tag4.items(), key=lambda x: x[1], reverse=True)
	for x in four:
		final.append(x)
	three = sorted(tag3.items(), key=lambda x: x[1], reverse=True)
	for x in three:
		final.append(x)
	two = sorted(tag2.items(), key=lambda x: x[1], reverse=True)
	for x in two:
		final.append(x)
	one = sorted(tag1.items(), key=lambda x: x[1], reverse=True)
	for x in one:
		final.append(x)
	


	#iterate through all photos and calculate numTopTags / totalTags
	# for key in countTopTags:
	# 	countTopTags[key] = countTopTags[key] / countTags[key] 

	#sorts by value in desc
	# sorted(countTopTags.items(), key=lambda x: x[1], reverse=True)	

	# for key in countTopTags:
	# 	#only get photos that have at least 1 of the top 5 tags
	# 	if countTopTags[key] != 0:
	# 		recommendedPhotos.append(key[1])

	return render_template('recommendedPhotos.html', photos = final, base64=base64)




	

if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
