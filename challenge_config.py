##-----------------------------------------------------------------------------
##
## challenge specific code and configuration
##
##-----------------------------------------------------------------------------


## A Synapse project will hold the assetts for your challenge. Put its
## synapse ID here, for example
## CHALLENGE_SYN_ID = "syn1234567"
CHALLENGE_SYN_ID = "syn4586419"

## Name of your challenge, defaults to the name of the challenge's project
CHALLENGE_NAME = "Example Synapse Challenge"

## Synapse user IDs of the challenge admins who will be notified by email
## about errors in the scoring script
ADMIN_USER_IDS = ["3324230"]

## Each question in your challenge should have an evaluation queue through
## which participants can submit their predictions or models. The queues
## should specify the challenge project as their content source. Queues
## can be created like so:
##   evaluation = syn.store(Evaluation(
##     name="My Challenge Q1",
##     description="Predict all the things!",
##     contentSource="syn1234567"))
## ...and found like this:
##   evaluations = list(syn.getEvaluationByContentSource('syn3375314'))
## Configuring them here as a list will save a round-trip to the server
## every time the script starts.

def validate(submission, template_location, key):
    challenge = {'challenge1':'SHEDDING_SC1','challenge2':'SYMPTOMATIC_SC2','challenge3':'LOGSYMPTSCORE_SC3'}
    goldstandard = pd.read_csv(gold[key])
    submission = pd.read_csv(submission)

    #CHECK: SUBJECTID must exist
    assert 'SUBJECTID' in submission, 'SUBJECTID must be one of the column headers\nYour column headers= %s' % ','.join(list(submission.columns))

    #CHECK: SHEDDING_SC1, SYMPTOMATIC_SC2, LOGSYMPTSCORE_SC3 columns must exist for respective challenge
    assert challenge[key] in submission, '%s must be one of the column headers for %s\nYour column headers= %s' % (challenge[key],key,','.join(list(submission.columns)))

    #CHECK: No duplicate SUBJECTIDs allowed
    assert all(~submission.duplicated('SUBJECTID')), 'No duplicate SUBJECTID allowed.\nDuplicated values=%s' % ','.join(submission[submission.duplicated('SUBJECTID')]['SUBJECTID'])

    #CHECK: Must contain SUBJECTIDs that exist in the template
    assert all(submission['SUBJECTID'].isin(goldstandard['SUBJECTID'])), 'Must have all SUBJECTIDs.\n%s not part of template SUBJECTIDs' % ','.join(submission[~submission['SUBJECTID'].isin(goldstandard['SUBJECTID'])]['SUBJECTID'])

    #CHECK: Must contain all SUBJECTIDs
    assert all(goldstandard['SUBJECTID'].isin(submission['SUBJECTID'])), "Can't have SUBJECTIDs that don't exist in the template.\nYou are missing %s" % ','.join(goldstandard[~goldstandard['SUBJECTID'].isin(submission['SUBJECTID'])])

    #CHECK: No NA values allowed
    assert sum(submission[challenge[key]].isnull())==0, 'NA values are not allowed'

    #CHECK: submissions must be all NA
    assert submission['SHEDDING_SC1'].dtype == 'float64' or submission['SHEDDING_SC1'].dtype == 'int64','Submissions must be numerical values'
    return(True)


def score_1_2:
    return(dict(),"Test")

def score_3(submission, template_location, key):
    
    goldstandard = pd.read_csv(gold[key])
    submission = pd.read_csv(submission)
    score = numpy.corrcoef(submission['LOGSYMPTSCORE_SC3'],goldstandard['LOGSYMPTSCORE_SC3'])[0, 1]
    return (dict(score=score),
            "Your score is: %.2f" % score)



evaluation_queues = [
dict(id = 5821575,q='1'), 
dict(id = 5821583,q='2'), 
dict(id = 5821621,q='3')]  


evaluation_queue_by_id = {q['id']:q for q in evaluation_queues}

## define the default set of columns that will make up the leaderboard
LEADERBOARD_COLUMNS = [
    dict(name='objectId',      display_name='ID',      columnType='STRING', maximumSize=20),
    dict(name='userId',        display_name='User',    columnType='STRING', maximumSize=20, renderer='userid'),
    dict(name='entityId',      display_name='Entity',  columnType='STRING', maximumSize=20, renderer='synapseid'),
    dict(name='versionNumber', display_name='Version', columnType='INTEGER'),
    dict(name='name',          display_name='Name',    columnType='STRING', maximumSize=240),
    dict(name='team',          display_name='Team',    columnType='STRING', maximumSize=240)]

## Here we're adding columns for the output of our scoring functions, score,
## rmse and auc to the basic leaderboard information. In general, different
## questions would typically have different scoring metrics.
leaderboard_columns = {}
for q in evaluation_queues:
    leaderboard_columns[q['id']] = LEADERBOARD_COLUMNS + [
        dict(name='score',         display_name='Score',   columnType='DOUBLE'),
        dict(name='rmse',          display_name='RMSE',    columnType='DOUBLE'),
        dict(name='auc',           display_name='AUC',     columnType='DOUBLE')]

## map each evaluation queues to the synapse ID of a table object
## where the table holds a leaderboard for that question
leaderboard_tables = {}

config_evaluations = [

    ## Q1
    {
        'id':5821575,
        'validation_function': validate,
        'scoring_function': score_1_2,
        'key': 'challenge1'

    },
    ##Q2
    {
        'id':5821583,
        'validation_function': validate,
        'scoring_function': score_1_2,
        'key': 'challenge1'


    },
    ##Q3
    {
        'id':5821621,
        'validation_function': validate,
        'scoring_function': score_3,
        'key': 'challenge1'

    }

]
config_evaluations_map = {ev['id']:ev for ev in config_evaluations}


def validate_submission(evaluation, submission):
    """
    Find the right validation function and validate the submission.

    :returns: (True, message) if validated, (False, message) if
              validation fails or throws exception
    """
    config = config_evaluations_map[int(evaluation.id)]
    validation_func = config['validation_function']
    template_location = "goldstandards"
    goldstandard = {'challenge1':os.path.join(template_location,'IDResilienceChallenge_SubmissionTemplate_SHEDDING_SC1.csv'),
            'challenge2':os.path.join(template_location,'IDResilienceChallenge_SubmissionTemplate_SYMPTOMATIC_SC2.csv'),
            'challenge3':os.path.join(template_location,'IDResilienceChallenge_SubmissionTemplate_LOGSYMPTSCORE_SC3.csv')}
   
    results = validation_func(submission,goldstandard[config['key']],config['key'])

    return results, "Looks OK to me!"


def score_submission(evaluation, submission):
    """
    Find the right scoring function and score the submission

    :returns: (score, message) where score is a dict of stats and message
              is text for display to user
    """
    config = config_evaluations_map[int(evaluation.id)]
    score_func = config['scoring_function']

    template_location = "goldstandards"
    goldstandard = {'challenge1':os.path.join(template_location,'IDResilienceChallenge_GoldStandard_SHEDDING_SC1.csv'),
            'challenge2':os.path.join(template_location,'IDResilienceChallenge_GoldStandard_SYMPTOMATIC_SC2.csv'),
            'challenge3':os.path.join(template_location,'IDResilienceChallenge_GoldStandard_LOGSYMPTSCORE_SC3.csv')}

    results = score_func(submission,goldstandard[config['key']],config['key'])

    return results


