##-----------------------------------------------------------------------------
##
## challenge specific code and configuration
##
##-----------------------------------------------------------------------------
import os
import pandas as pd
import numpy as np
import sklearn
import decimal
from sklearn.metrics import auc
from multiprocessing import Pool
## A Synapse project will hold the assetts for your challenge. Put its
## synapse ID here, for example
## CHALLENGE_SYN_ID = "syn1234567"
CHALLENGE_SYN_ID = "syn4586419"

## Name of your challenge, defaults to the name of the challenge's project
CHALLENGE_NAME = "Example Synapse Challenge"

## Synapse user IDs of the challenge admins who will be notified by email
## about errors in the scoring script
ADMIN_USER_IDS = ["3324230"]


##Challenge validation / scoring ###
challenge = {'challenge1':'SHEDDING_SC1','challenge2':'SYMPTOMATIC_SC2','challenge3':'LOGSYMPTSCORE_SC3'}

def validate(submission, goldstandard, key):
    goldstandard = pd.read_csv(goldstandard)
    try:
        submission = pd.read_csv(submission)
    except Exception as e:
        raise ValueError("Submitted file must be a comma-delimited file")

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
    assert submission[challenge[key]].dtype == 'float64' or submission[challenge[key]].dtype == 'int64','Submissions must be numerical values'
    return(True)

#SCORE 1,2 HELPER FUNCTIONS
def __nonlinear_interpolated_evalStats(block_df, blockWise_stats):
    """
    // given a block* of submitted belief score and blockwise statistics (see:__get_blockWise_stats)
    calculates the Precision, Recall & False Positive Rate 
    *A block by definition should have the same belief score
   
    """
    blockValue = block_df.predict.unique()
    if len(blockValue) != 1:
        raise Exception("grouping by predict column doesnt yield unique predict vals per group..WIERD")
    blockValue = blockValue[0]
    blockStats = blockWise_stats[blockWise_stats.blockValue == blockValue].squeeze() #squeeze will convert one row df to series
    
    block_precision = []
    block_recall = []
    block_fpr = []
    total_elements = blockWise_stats.cum_numElements.max()
    total_truePos = blockWise_stats.cum_truePos.max()
    total_trueNeg = total_elements - total_truePos
    for block_depth,row in enumerate(block_df.iterrows()):
        block_depth += 1  #increase block depth by 1 
        row = row[1]
        #calculate the cumulative true positives seen till the last block from the current active block
        # and the total number of elements(cumulative) seen till the last block
        if blockStats.block == 1: #no previous obviously
            cum_truePos_till_lastBlock = 0
            cum_numElements_till_lastBlock = 0
            cum_trueNeg_till_lastBlock = 0
        elif blockStats.block > 1:
            last_blockStats = blockWise_stats[blockWise_stats.block == (blockStats.block-1)].squeeze()
            cum_truePos_till_lastBlock = last_blockStats['cum_truePos']
            cum_numElements_till_lastBlock = last_blockStats['cum_numElements']
            cum_trueNeg_till_lastBlock = cum_numElements_till_lastBlock - cum_truePos_till_lastBlock
            
        truePos = cum_truePos_till_lastBlock + (blockStats.block_truePos_density*block_depth)
        falsePos = cum_trueNeg_till_lastBlock + ((1 - blockStats.block_truePos_density ) * block_depth)
        
        #precision
        interpolated_precision = truePos /(cum_numElements_till_lastBlock+block_depth)
        block_precision.append(interpolated_precision)
        #recall == true positive rate
        interpolated_recall = truePos /total_truePos
        block_recall.append(interpolated_recall)
        #fpr == false positive rate
        interpolated_fpr = falsePos / total_trueNeg
        block_fpr.append(interpolated_fpr)
        
    block_df['precision'] = block_precision
    block_df['recall'] = block_recall
    block_df['fpr'] = block_fpr
    block_df['block_depth'] = np.arange(1,block_df.shape[0]+1)
    block_df['block'] = blockStats.block
    return(block_df)


def __get_blockWise_stats(sub_stats):
    """
    calculate stats for each block of belief scores
    """
    pd.options.mode.chained_assignment = None
    #group to calculate group wise stats for each block
    grouped = sub_stats.groupby(['predict'], sort=False)
    
    #instantiate a pandas dataframe to store the results for each group (tied values)
    result = pd.DataFrame.from_dict({'block':xrange(len(grouped)),
                                         'block_numElements'  : np.nan,
                                         'block_truePos_density' : np.nan,
                                         'block_truePos'      : np.nan,
                                         'blockValue'   : np.nan
                                         })
    
    for block,grp in enumerate(grouped):
        name,grp = grp[0],grp[1]
        truePositive = sum(grp.truth == 1)
        grp_truePositive_density = truePositive / float(len(grp))
        idxs = result.block == block
        result.block_truePos_density[idxs] = grp_truePositive_density
        result.block_numElements[idxs] = len(grp)
        result.block_truePos[idxs] = truePositive
        result.blockValue[idxs] = grp.predict.unique()
    result.block = result.block + 1
    result['cum_numElements'] = result.block_numElements.cumsum()
    result['cum_truePos'] = result.block_truePos.cumsum()
    return(result)


def getAUROC_PR(sub_stats):
    #calculate blockwise stats for tied precdiction scores
    blockWise_stats = __get_blockWise_stats(sub_stats)
    
    #calculate precision recall & fpr for each block
    grouped = sub_stats.groupby(['predict'],sort=False)
    sub_stats = grouped.apply(__nonlinear_interpolated_evalStats,blockWise_stats)
    
    precision, recall,  fpr, threshold = sub_stats.precision, sub_stats.recall, sub_stats.fpr, sub_stats.predict 
    tpr = recall #(Recall and True positive rates are same)
    roc_auc = auc(fpr,tpr,reorder=True)

    #PR curve AUC (Fixes error when prediction == truth)
    recall_new=list(recall)
    precision_new=list(precision)
    recall_new.reverse()
    recall_new.append(0)
    recall_new.reverse()

    precision_new.reverse()
    precision_new.append(precision_new[len(precision_new)-1])
    precision_new.reverse()

    PR_auc = auc(recall_new, precision_new,reorder=True)
    #results = [ round(x,4) for x in results]
    return(roc_auc,PR_auc)


def score_1_2(submission, goldstandard, key):
    goldstandard = pd.read_csv(goldstandard)
    submission = pd.read_csv(submission)
    submission = submission.sort_values('SUBJECTID')
    goldstandard = goldstandard.sort_values('SUBJECTID')

    sub_stats = pd.DataFrame.from_dict({'predict':submission[challenge[key]], 'truth':goldstandard[challenge[key]]}, dtype='float64')
    sub_stats = sub_stats.sort_values(['predict'],ascending=False)
    true_auroc, true_aupr = getAUROC_PR(sub_stats)
    shuffled = dict()
    permute_times = 10000
    for i in xrange(permute_times):
        np.random.shuffle(sub_stats['predict'].values)
        sub_stats = sub_stats.reset_index()
        del sub_stats['index']
        shuffled[i] = sub_stats

    mp = Pool(2)
    temp = mp.map(getAUROC_PR,shuffled.values())
    auroc_total = []
    aupr_total = []
    for auc, pr in temp:
        auroc_total.append(auc)
        aupr_total.append(pr)

    pVal_ROC = decimal.Decimal(sum(auroc_total >= np.float64(true_auroc))) / decimal.Decimal(permute_times+1)
    pVal_PR = decimal.Decimal(sum(aupr_total >= np.float64(true_aupr))) / decimal.Decimal(permute_times+1)

    return(dict(AUROC = true_auroc, AUPR = true_aupr, nAUROC_pVal = pVal_ROC, nAUPR_pVal=pVal_PR),
            "Thank you for your submission. Your submission has been validated and scored. Stay tuned for results on the challenge site at the end of each challenge phase.")

def score_3(submission, goldstandard, key):
    goldstandard = pd.read_csv(goldstandard)
    submission = pd.read_csv(submission)
    submission = submission.sort_values('SUBJECTID')
    goldstandard = goldstandard.sort_values('SUBJECTID')
    score = np.corrcoef(submission[challenge[key]],goldstandard[challenge[key]])[0, 1]

    total = []
    permute_times = 10000
    for i in xrange(permute_times):
        np.random.shuffle(submission[challenge[key]].values)
        temp = np.corrcoef(submission[challenge[key]],goldstandard[challenge[key]])[0, 1]
        total.append(temp)

    pVal = decimal.Decimal(sum(total >= score)) / decimal.Decimal(permute_times+1)

    return (dict(score=score, pVal = pVal),
            "Thank you for your submission. Your submission has been validated and scored. Stay tuned for results on the challenge site at the end of each challenge phase.")


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
leaderboard_columns[5821575] = LEADERBOARD_COLUMNS + [
    Column(name='AUPR',         display_name='AUPR',   columnType='DOUBLE'),
    Column(name='AUROC',          display_name='AUROC',    columnType='DOUBLE'),
    Column(name='nAUPR_pVal',           display_name='nAUPR_pVal',     columnType='DOUBLE'),
    Column(name='nAUROC_pVal',           display_name='nAUROC_pVal',     columnType='DOUBLE')]

leaderboard_columns[5821583] = leaderboard_columns[5821575]
leaderboard_columns[5821621] = LEADERBOARD_COLUMNS + [
    Column(name='score',         display_name='Correlation',   columnType='DOUBLE'),
    Column(name='pVal',          display_name='pVal',    columnType='DOUBLE')]


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
        'key': 'challenge2'


    },
    ##Q3
    {
        'id':5821621,
        'validation_function': validate,
        'scoring_function': score_3,
        'key': 'challenge3'

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
   
    results = validation_func(submission.filePath,goldstandard[config['key']],config['key'])

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

    results = score_func(submission.filePath,goldstandard[config['key']],config['key'])

    return results


