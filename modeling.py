#!/usr/bin/env python

#starting point: train, val, test in memory from data_prep

def dummy_run(spark):
    train=spark.createDataFrame(
    [
        (82, 124, 5.0),
        (64, 123, 4.0),
        (27, 122, 3.0),
        (25, 122, 1.0),
        (12, 124, 2.0)
    ],
    ['user_id', 'book_id', 'rating'] 
    )

    val=spark.createDataFrame(
    [
        (82, 123, 5.0),
        (64, 122, 4.0),
        (27, 124, 3.0),
        (64, 123, 2.0),
        (12, 122, 4.0)
    ],
    ['user_id', 'book_id', 'rating'] 
    )
    
    predictions=als(spark, train, val, lamb=0.01, rank=3)
    print(predictions)
    print(type(predictions))
    predictions.show()
    return 

def als(spark, train, val, lamb, rank):
    ''' 
        Fits ALS model from train and makes predictions 
        Imput: training file
        arguments:
            spark - spark
            lamba - 
            rank - 
        Returns: Predictions generated by als 
    Notes: 
        https://spark.apache.org/docs/2.2.0/ml-collaborative-filtering.html
        - Don't need to consider alpha bc using explicit feedback
        - Assignment readme : only need to tune rank and lambda...will leave other als params 
        - Question: not sure what to do about the nonnegative param in als "specifies whether or not to
         use nonnegative constraints for least squares (defaults to false)"
        - "Currently the supported cold start strategies are 'nan' and 'drop'. Spark allows users to set the 
        coldStartStrategy parameter to “drop” in order to drop any rows in the DataFrame of predictions that contain NaN values. 
        The evaluation metric will then be computed over the non-NaN data and will be valid" 
       
    '''
    from pyspark.ml.recommendation import ALS

    als = ALS(rank = rank, regParam=lamb, userCol="user_id", itemCol="book_id", ratingCol='rating', implicitPrefs=False, coldStartStrategy="drop")
    model = als.fit(train)
   
    predictions = model.transform(val)
    return predictions

def hyperparam_search(spark, train, val, k=500):
    ''' 
        Fits ALS model from train, ranks k top items, and evaluates with MAP, P, NDCG across combos of rank/lambda hyperparameter
        Imput: training file
        arguments:
            spark - spark
            train - training set
            val - validation set 
            k - how many top items to predict (default = 500)
        Returns: MAP, P, NDCG for each model
    '''
     from pyspark.ml.recommendation import ALS
     from pyspark.mllib.evaluation import RankingMetrics
     import pyspark.sql.functions as F
     from pyspark.sql.functions import expr

    # Tune hyper-parameters with cross-validation 
    # references https://spark.apache.org/docs/latest/api/python/pyspark.ml.html#pyspark.ml.tuning.CrossValidator
    # https://spark.apache.org/docs/latest/ml-tuning.html
    # https://github.com/nyu-big-data/lab-mllib-not-assignment-ldarinzo/blob/master/supervised_train.py
    #https://vinta.ws/code/spark-ml-cookbook-pyspark.html

    #for all users in val set, get list of books they actually read
    user_id = val.select('user_id').distinct()
    true_label = val.select('user_id', 'book_id')\
                .groupBy('user_id')\
                .agg(expr('collect_list(book_id) as true_item'))

    #build paramGrid lambda/rank combos
    paramGrid = ParamGridBuilder() \
        .addGrid(als.regParam, [0.0001, 0.001, 0.01, 0.1, 1, 10]) \
        .addGrid(als.rank, [5, 10, 20, 100, 500]) \
        .build()

    #fit and evaluate for all combos
    for i in param_grid:
        als = ALS(rank = i[1], regParam=i[0], userCol="user_id", itemCol="book_id", ratingCol='rating', implicitPrefs=False, coldStartStrategy="drop")
        model = als.fit(train)

        recs = model.recommendForUserSubset(user_id, k)
        pred_label = recs.select('user_id','recommendations.book_id')

        pred_true_rdd = pred_label.join(F.broadcast(true_label), 'user_id', 'inner') \
                    .rdd \
                    .map(lambda row: (row[1], row[2]))

        metrics = RankingMetrics(pred_true_rdd)
        mean_ap = metrics.meanAveragePrecision
        ndcg_at_k = metrics.ndcgAt(k)
        p_at_k= metrics.precisionAt(k)
        print(i, 'MAP: ', mean_ap , 'NDCG: ', ndcg_at_k, 'Precision at k: ', p_at_k)








