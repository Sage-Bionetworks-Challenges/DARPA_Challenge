> Moved from https://github.com/Sage-Bionetworks/DARPA_Challenge

Challenge Template for Python
=============================

For those writing Synapse challenge scoring applications in Python, these scripts should serve as a starting point giving working examples of many of the tasks typical to running a challenge on Synapse. [Creating a Challenge Space in Synapse](http://docs.synapse.org/articles/challenge_administration.html) is a step-by-step guide to building out a challenge.

### Validation and Scoring

Let's validate the submission we just reset, with the full suite of messages enabled:

    python challenge.py --send-messages --notifications --acknowledge-receipt validate [evaluation ID]

The script also takes a --dry-run parameter for testing. Let's see if scoring seems to work:

    python challenge.py --send-messages --notifications --dry-run score [evaluation ID]

OK, assuming that went well, now let's score for real:

    python challenge.py --send-messages --notifications score [evaluation ID]


### Setting Up Automatic Validation and Scoring on an EC2

Make sure challenge_config.py is set up properly and all the files in this repository are in one directory on the EC2.  Crontab is used to help run the validation and scoring command automatically.  To set up crontab, first open the crontab configuration file:

	crontab -e

Paste this into the file:

	# minute (m), hour (h), day of month (dom), month (mon)                      
	*/10 * * * * sh challenge_eval.sh>>~/challenge_runtimes.log
	5 5 * * * sh scorelog_update.sh>>~/change_score.log

Note: the first 5 * stand for minute (m), hour (h), day of month (dom), and month (mon). The configuration to have a job be done every ten minutes would look something like */10 * * * *
