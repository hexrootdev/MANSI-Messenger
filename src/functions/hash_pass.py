import bcrypt

def hash_password(raw: str):
    password_bytes = raw.encode('utf-8')
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    
    return hashed_password.decode('utf-8')

def check_password(uinput: str, hashed_password: str):
    return bcrypt.checkpw(uinput.encode('utf-8'), hashed_password.encode('utf-8'))