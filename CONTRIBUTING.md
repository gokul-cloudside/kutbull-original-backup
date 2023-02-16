Updated list of python packages:
Keep an updated list of python packages that are needed to run the code in this repository. Follow the following steps:
(a) Keep a list of packages in the requirements.txt
(b) Enable python virtual environment : http://docs.python-guide.org/en/latest/dev/virtualenvs/. It essentially creates a separate python installation for each repository (create a new environment in the directory where the code is) and the packages list can be tracked via pip.
(c) Enable and disable virtual environment in the directory where the code for this repository resides.
(d) The list of packages needed can be installed as 'pip install -r requirements.txt'
(e) If you add any new python package, update the requirements.txt as 'pip freeze > requirements.txt'

Git standards:
(a) The latest code will always reside in the master branch. If you are working on a new set of features, please clone the master branch (or the other based on your needs) and send a merge request to the branch owner.
(b) Please follow standard git practices: Commit Related Changes, Commit Often, Don’t Commit Half-Done Work, Test Before You Commit, Write Good Commit Messages, Version Control is not a Backup System, Use Branches, Agree on a Workflow. More details here: 
http://www.git-tower.com/learn/git/ebook/command-line/appendix/best-practices (Obviously this is not a complete list)

Testing:
(a) A feature should be committed to the master branch only if it has been tested by at least one other person. Please write your test case thoroughly, and assign it to someone else who has knowledge on that part.
(TODO : Sunil to send more details on this later).

Programming style:
(a) Python generally keeps the code clean as the indentation needs to happen. Please use tab as a set of 4 spaces.