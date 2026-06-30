# coding=utf-8

import os


base_path = os.getcwd()
print("common os.getcwd:" + base_path)

def set_base_path(path):
    global base_path
    base_path = path
    print("common base_path:" + base_path)

if __name__== "__main__" :
    pass
    #build()

