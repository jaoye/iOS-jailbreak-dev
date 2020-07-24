import os
import random
import binascii

def process_nib(payload_path):

    for root, dirs, files in os.walk(payload_path):
        for file in files:
            file_path = os.path.join(root, file)
            # print file_path
            
            if file_path.lower().endswith('.sqlite'):
                print 'over sqlite'
                continue
            if file_path.lower().endswith('.plist'):
                continue
            f=open(file_path,"ab")
            num=random.randint(2,25);
            for i in range(0,num*4):
                f.write(binascii.unhexlify('00'))
            f.close()

process_nib("./callery/res2")
