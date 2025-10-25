from flask import Flask,render_template,request,redirect,url_for,flash,session,send_file
from flask_session import Session
from otp import genotp
from cmail import send_mail
from stoken import endata,dedata
import mysql.connector
import flask_excel as excel
from io import BytesIO
import re

from mimetypes import guess_type
from mysql.connector import connection
mydb=connection.MySQLConnection(user='root',password='admin',host='localhost',db='snmdb')
app=Flask(__name__)
excel.init_excel(app)
app.config['SESSION_TYPE']='filesystem'
Session(app)
app.secret_key='123456789'
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/register',methods=['GET','POST'])  
def register():
    if request.method=="POST":
        username=request.form['username']  
        usermail=request.form['usermail']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from user where usermail=%s',[usermail])
        count_usermail=cursor.fetchone()
        if count_usermail[0]==0:
            gotp=genotp() #server generated opt
            userdata={'username':username,'usermail':usermail,'password':password,'otp':gotp}
            subject='OTP for simple notes management system'
            body=f'use the given otp for verification {gotp}'
            send_mail(to=usermail,subject=subject,body=body)
            flash(f'otp has been sent to given mail {usermail}')
            return redirect(url_for('otpverify',udata=endata(data=userdata))) # encrypting otp data
        elif count_usermail[0]==1:
            flash('user email already existed pls check email')
            return redirect(url_for('register'))    
    return render_template('register.html')  
@app.route('/otpverify/<udata>',methods=['GET','POST'])   
def otpverify(udata):
    if request.method=='POST':
        user_otp=request.form['otp']
        de_userdata=dedata(data=udata) #decrytiping encrypted otp data
        print(de_userdata)
        if de_userdata['otp']==user_otp:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into user(username,usermail,password) values(%s,%s,%s)',[de_userdata['username'],de_userdata['usermail'],de_userdata['password']])
            mydb.commit()
            cursor.close()
            flash(f'successfully registered pls login')

            return 'login'
        else:
            flash('otp is wrong')
            return redirect(url_for('otpverify',udata=udata))

        
    return render_template('otp.html')  
#login route
@app.route('/userlogin',methods=['GET','POST'])
def userlogin():
    if not session.get('user'):
        if request.method=='POST':
            login_usermail=request.form['usermail']
            login_password=request.form['password']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from user where usermail=%s',[login_usermail])
            count_usermail=cursor.fetchone()
            print(count_usermail)#(1,) if no account found(0,)
            if count_usermail[0]==1:
                cursor.execute('select password from user where usermail=%s',[login_usermail])
                stored_password=cursor.fetchone()
                if stored_password[0]==login_password:
                    session['user']=login_usermail
                    return redirect(url_for('dashboard'))
                else:
                    flash('password is incorrect')
                    return redirect(url_for('userlogin'))
            else:
                flash('usermail is not registered')
                return redirect(url_for('userlogin'))
        
        return render_template('login.html')
    else:
        return redirect(url_for('dashboard'))
    

@app.route('/dashboard')
def dashboard():
    if session.get('user'):
        return render_template('dashboard.html')
    else:
        flash('pls login first')
        return redirect(url_for(userlogin))
    
@app.route('/userlogout')
def userlogout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('userlogin'))
    else:
        flash('pls login first')
        return redirect(url_for('userlogin'))
    
@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    if request.method=='POST':
        print(request.form)
        title=request.form['title']
        description=request.form['description']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from user where usermail=%s',[session.get('user')])
        user_id=cursor.fetchone()#(1,)
        cursor.execute('insert into notesdata(title,description,added_by) values(%s,%s,%s)',[title,description,user_id[0]])
        mydb.commit()
        flash('note added successfully')
    return render_template('addnotes.html')
@app.route('/view_allnotes')
def view_allnotes():
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select userid from user where usermail=%s',[session.get('user')])
    user_id=cursor.fetchone()#(1,)
    cursor.execute('select notesid,title,created_at from notesdata where added_by=%s',[user_id[0]])
    stored_notesdata=cursor.fetchall()
    print(stored_notesdata)
    return render_template('view_allnotes.html',ndata=stored_notesdata)
@app.route('/view_notes/<nid>')
def view_notes(nid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select * from notesdata where notesid=%s',[nid])
    stored_notesdata=cursor.fetchone()
    print(stored_notesdata)
    return render_template('view_notes.html',stored_notesdata=stored_notesdata)
@app.route('/deletenotes/<nid>')
def deletenotes(nid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('delete from notesdata where notesid=%s',[nid])
    mydb.commit()
    cursor.close()
    flash('note deleted successfully')
    return redirect(url_for('view_allnotes'))
@app.route('/update_notes/<nid>',methods=['GET','POST'])
def update_notes(nid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select * from notesdata where notesid=%s',[nid])
    stored_notesdata=cursor.fetchone()
    print(stored_notesdata)
    if request.method=='POST':
        updated_title=request.form['title']
        updated_description=request.form['description']
        cursor.execute('update notesdata set title=%s,description=%s where notesid=%s',[updated_title,updated_description,nid])
        mydb.commit()
        cursor.close()
        flash('note updated successfully')
        return redirect(url_for('view_notes',nid=nid))
    return render_template('updatenotes.html',stored_notesdata=stored_notesdata)
@app.route('/fileupload',methods=['GET','POST'])
def fileupload():
    if request.method=='POST':
        filedata=request.files['file']
        fname=filedata.filename
        fdata=filedata.read()
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from user where usermail=%s',[session.get('user')])
        user_id=cursor.fetchone()#(1,)
        cursor.execute('insert into file_data(filename,filedata,added_by) values(%s,%s,%s)',[fname,fdata,user_id[0]])
        mydb.commit()
        flash(f'{fname} file added successfully')
        return redirect(url_for('view_allfiles'))
    return render_template('fileupload.html')
@app.route('/view_allfiles')
def view_allfiles():
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select userid from user where usermail=%s',[session.get('user')])
    user_id=cursor.fetchone()#(1,)
    cursor.execute('select fid,filename,created_at from file_data where added_by=%s',[user_id[0]])
    stored_filedata=cursor.fetchall()
    print(stored_filedata)
    return render_template('view_allfiles.html',ndata=stored_filedata)
@app.route('/view_file/<fid>')
def view_file(fid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select * from file_data where fid=%s',[fid])
    fdata=cursor.fetchone()
    array_data=BytesIO(fdata[2])
    mime_type,_=guess_type(fdata[1])
    print(mime_type)
    return send_file(array_data,mimetype=mime_type or 'application/octat-stream',as_attachment=False,download_name=fdata[1])
@app.route('/download_file/<fid>')
def download_file(fid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select * from file_data where fid=%s',[fid])
    fdata=cursor.fetchone()
    array_data=BytesIO(fdata[2])
    mime_type,_=guess_type(fdata[1])
    print(mime_type)
    return send_file(array_data,mimetype=mime_type or 'application/octat-stream',as_attachment=True,download_name=fdata[1])
@app.route('/delete_file/<fid>')
def delete_file(fid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('delete from file_data where fid=%s',[fid])
    mydb.commit()
    cursor.close()
    flash('file deleted successfully')
    return redirect(url_for('view_allfiles'))
@app.route('/getexceldata')
def getexceldata():
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from user where usermail=%s',[session.get('user')])
        user_id=cursor.fetchone()#(1,)
        cursor.execute('select notesid,title,description,created_at from notesdata where added_by=%s',[user_id[0]])
        userdata=cursor.fetchall()
        headling=['Notesid','Title','Description','Created_at']
        array=[list(i) for i in userdata]
        array.insert(0,headling)
        return excel.make_response_from_array(array,'xlsx',file_name='notesexcel')
    else:
        flash('pls login first')
        return redirect(url_for('userlogin'))
@app.route('/search',methods=['GET','POST'])
def search():
    if session.get('user'):
        usersearch=request.form['search']
        strg=['A-Za-z0-9']
        pattern=re.compile(f'^{strg}',re.IGNORECASE)
        if pattern.match(usersearch):
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from user where usermail=%s',[session.get('user')])
            user_id=cursor.fetchone()#(1,)
            cursor.execute('select notesid,title,description,created_at from notesdata where (notesid like %s or title like %s or description like %s or created_at like %s) and added_by=%s',[usersearch+'%',usersearch+'%',usersearch+'%',usersearch+'%',user_id[0]])
            resultsearch=cursor.fetchall()
            cursor.execute('select fid,filename,created_at from file_data where fid like %s or filename like %s or created_at like %s and added_by=%s',[usersearch+'%',usersearch+'%',usersearch+'%',user_id[0]])
            resultfile=cursor.fetchall()
        
            return render_template('dashboard.html',resultsearch=resultsearch,resultfile=resultfile)
        else:
            flash('invalid search input')
            return redirect('dashboard.html')
    else:
        flash('pls login first')
        return redirect(url_for('userlogin'))
@app.route('/fgtpwd',methods=['GET','POST'])
def fgtpwd():
    if request.method=='POST':
        user_email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from user where usermail=%s',[user_email])
        count_usermail=cursor.fetchone()#account (1,) if not account (0,)
        if count_usermail[0]==1:
            subject='reset link for password update Simple Notes Management System'
            body=f"use the given reset link for password update {url_for('confirmpwd',udata=endata(data=user_email),_external=True)}"
            send_mail(to=user_email,subject=subject,body=body)
            flash(f'reset link has been sent to given mail {user_email}')
            return redirect(url_for('fgtpwd'))
        elif count_usermail[0]==0:
            flash('user email not found pls check email')
            return redirect(url_for('register'))
    return render_template('forgotpassword.html')
@app.route('/confirmpwd/<udata>',methods=['GET','PUT'])
def confirmpwd(udata):
    if request.method=='PUT':
        npwd=request.get_json('password')['password']
        print(npwd)
        de_udata=dedata(udata)
        cursor=mydb.cursor(buffered=True)
        cursor.execute('update user set password=%s where usermail=%s',[npwd,de_udata])
        mydb.commit()
        cursor.close()
        flash('new password updated successfully')
        return 'ok'
    return render_template('npassword.html',udata=udata)

    return 'update password'
if __name__=="__main__":
    app.run(debug=True,use_reloader=True)
