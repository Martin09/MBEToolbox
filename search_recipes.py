"""
Scripts to search through old MBE recipes looking for specific keywords
"""
from glob import glob

path = 'Recipes_Growth'

files = glob(path + '/*.py')

keywords = ['Sb']

for file in files:
    # Search filename for keyword
    for keyword in keywords:
        if keyword.lower() in file.lower():
            print(file)

    # Search each line for keyword
    for line in open(file):
        for keyword in keywords:
            if keyword.lower() in line.lower():
                print(file)

print('Done!')