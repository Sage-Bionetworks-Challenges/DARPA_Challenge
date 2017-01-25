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


#--------------------
#Archive and Rank
#--------------------
# python challenge.py archive 5821575
# python challenge.py rank 5821575

# python challenge.py archive 5821583
# python challenge.py rank 5821583

# python challenge.py archive 5821621
# python challenge.py rank 5821621

# python challenge.py archive 7991328
# python challenge.py rank 7991328

# python challenge.py archive 7991330
# python challenge.py rank 7991330

# python challenge.py archive 7991332
# python challenge.py rank 7991332