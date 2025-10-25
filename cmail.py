import smtplib  #to send email from one mail another
from email.message import EmailMessage #module used to create email template
def send_mail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465) #creating server object for gmail
    server.login('ajaykumarsaikam@gmail.com','cpgj nzrz jwxq sfgn') #login to gmail
    msg=EmailMessage()
    msg['FROM']='ajaykumarsaikam@gmail.com'
    msg['TO']=to
    msg['SUBJECT']=subject
    msg.set_content(body)
    server.send_message(msg)
    server.close()