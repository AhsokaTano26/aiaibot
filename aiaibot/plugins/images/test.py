import hashlib

def encrypt(txt):
    md5_obj = hashlib.md5()
    md5_obj.update(txt.encode())
    md5_result = md5_obj.hexdigest()
    return md5_result

if __name__ == '__main__':
    folder_name = str(input("<UNK>"))
    extra_name = str(input("<UNK2>"))
    id = folder_name + "-" + extra_name
    id = encrypt(id)
    print(id)