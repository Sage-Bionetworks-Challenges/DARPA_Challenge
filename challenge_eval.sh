# Automation of validation and scoring
# Make sure you point to the directory where challenge.py belongs and a log directory must exist for the output
cd ~/DARPA_Challenge
#---------------------
#Validate submissions
#---------------------
python challenge.py -u DARPA --send-messages --notifications validate --all >> log/score.log 2>&1

#--------------------
#Score submissions
#--------------------
python challenge.py -u DARPA --send-messages --notifications score --all >> log/score.log 2>&1
