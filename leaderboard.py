from synapseclient import Project, File, Folder
from synapseclient import Schema, Column, Table, Row, RowSet, as_table_columns
from datetime import datetime
## define the default set of columns that will make up the leaderboard
LEADERBOARD_COLUMNS = [
    Column(name='objectId',      display_name='ID',      columnType='STRING', maximumSize=20),
    Column(name='userId',        display_name='User',    columnType='STRING', maximumSize=20),
    Column(name='entityId',      display_name='Entity',  columnType='ENTITYID'),
    Column(name='name',          display_name='Name',    columnType='STRING', maximumSize=1000),
    Column(name='team',          display_name='Team',    columnType='STRING', maximumSize=1000),
    Column(name='submitDate',    display_name='submitDate',    columnType='DATE')]

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
############################################################

project = "syn5641757"
evaluation = [5821575,5821583,5821621]
evaluationName = {5821575:"DARPA-SC1",5821583:"DARPA-SC2",5821621:"DARPA-SC3"}

#Create leaderboard tables
for i in evaluation:
    create_leaderboard_table(i,leaderboard_columns[i],evaluationName[i],project)

def create_leaderboard_table(evaluation,cols,name,parent):
    temp = syn.query('select id,name from table where projectId == "%s" and name == "%s"' % (parent,name))
    if temp['totalNumberOfResults'] == 0:
        schema = syn.store(Schema(name=name, columns=cols, parent=project))
    else:
        schema = syn.get(temp['results'][0]['table.id'])
    for submission, status in syn.getSubmissionBundles(evaluation,status='SCORED'):
        annotations = synapseclient.annotations.from_submission_status_annotations(status.annotations) if 'annotations' in status else {}
        update_leaderboard_table(schema.id, submission, annotations)

def update_leaderboard_table(leaderboard_table, submission, fields):
    """
    Insert or update a record in a leaderboard table for a submission.

    :param fields: a dictionary including all scoring statistics plus the team name for the submission.
    """
    if submission.get('teamId', None) is not None:
        temp = syn.getTeam(submission.teamId)
        fields['team'] = foo.name
    else:
        temp = syn.getUserProfile(submission.userId)
        fields['team'] = temp.userName
    ## copy fields from submission
    ## fields should already contain scoring stats
    fields['objectId'] = submission.id
    fields['userId'] = submission.userId
    fields['entityId'] = submission.entityId
    fields['submitDate'] = synapseclient.utils.to_unix_epoch_time(datetime.strptime(submission.createdOn,"%Y-%m-%dT%H:%M:%S.%fZ"))
    fields['name'] = submission.name

    results = syn.tableQuery("select * from %s where objectId=%s" % (leaderboard_table, submission.id), resultsAs="rowset")
    rowset = results.asRowSet()

    ## figure out if we're inserting or updating
    if len(rowset['rows']) == 0:
        row = {'values':[]}
        rowset['rows'].append(row)
        mode = 'insert'
    elif len(rowset['rows']) == 1:
        row = rowset['rows'][0]
        mode = 'update'
    else:
        ## shouldn't happen
        raise RuntimeError("Multiple entries in leaderboard table %s for submission %s" % (leaderboard_table,submission.id))

    ## build list of fields in proper order according to headers
    row['values'] = [fields.get(col['name'], None) for col in rowset['headers']]

    return syn.store(rowset)


###### RETURN RANKING FOR LEADERBOARD FOR SC1, 2######

def sorting(dfcolumn,ascending=False):
    i=1
    ranking=[1]
    sorteddf = dfcolumn.sort_values(ascending=ascending)
    first = sorteddf[0]
    for value in sorteddf[1:]:
        if value == first:
            ranking.append(i)
        else:
            i = i+1
            ranking.append(i)
        first = value
    return(ranking)


def addRanking_SC1_2(x):
    temp = syn.getSubmissionStatus(x['objectId'])
    temp.annotations['stringAnnos'].append({'isPrivate':False,'key':'AUPRpVal_boolean','value':x['AUPRpVal_boolean']})
    temp.annotations['stringAnnos'].append({'isPrivate':False,'key':'AUROCpVal_boolean','value':x['AUROCpVal_boolean']})
    temp.annotations['doubleAnnos'].append({'isPrivate':False,'key':'finalRank','value':x['final_rank']})
    syn.store(temp)

def addRanking_SC3(x):
    temp = syn.getSubmissionStatus(x['objectId'])
    temp.annotations['stringAnnos'].append({'isPrivate':False,'key':'booleanpVal','value':x['pVal_boolean']})
    temp.annotations['doubleAnnos'].append({'isPrivate':False,'key':'finalRank','value':x['final_rank']})
    syn.store(temp)


def SC1_2_ranking(synId):
    rankings = syn.tableQuery('SELECT * FROM %s' % synId)
    rankingsdf = rankings.asDataFrame()
    rankingsdf['AUPR_rank'] = sorting(rankingsdf['AUPR'])
    rankingsdf['AUROC_rank'] = sorting(rankingsdf['AUROC'])
    rankingsdf['average_rank'] = (rankingsdf['AUPR_rank'] + rankingsdf['AUROC_rank'])/2
    rankingsdf['final_rank'] = sorting(rankingsdf['average_rank'],True)
    rankingsdf['AUPRpVal_boolean'] = rankingsdf['nAUPR_pVal'] < 0.05
    rankingsdf['AUROCpVal_boolean'] = rankingsdf['nAUROC_pVal'] < 0.05
    rankingsdf.apply(lambda x: addRanking_SC1_2(x),axis=1)

def SC3_ranking(synId):
   ##### SC3
    rankings = syn.tableQuery('SELECT * FROM syn6088409')
    rankingsdf = rankings.asDataFrame()
    rankingsdf['final_rank'] = sorting(rankingsdf['score'])
    rankingsdf['pVal_boolean'] = rankingsdf['pVal'] < 0.05
    rankingsdf.apply(lambda x: addRanking_SC3(x),axis=1) 

SC1_2_ranking("syn6088407")
SC1_2_ranking("syn6088408")
SC3_ranking("syn6088409")



