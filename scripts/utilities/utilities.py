import re
import sklearn
import scipy
from scipy.cluster import hierarchy as hc
import pandas as pd
from pandas.api.types import is_string_dtype, is_numeric_dtype, is_categorical_dtype
import numpy as np
import matplotlib.pyplot as plt

def display_all(df):
    '''
    display more rows and columns of a dataframe in ipython
    '''
    with pd.option_context('display.max_rows', 1000, 'display.max_columns', 1000):
        display(df)


def get_datepart(df, fieldName, drop = True, time = False):
    '''
    create multiple columns based on a date column which capture more granular information
    '''
    temp = re.sub("[Dd]ate$","",fieldName) +"_"
    attr = ['Year', 'Month', 'Week', 'Day', 'Dayofweek', 'Dayofyear',"weekofyear",'Is_month_end', 'Is_month_start', 
         'Is_quarter_end', 'Is_quarter_start', 'Is_year_end', 'Is_year_start']
    if time:
        attr = attr + ['Hour', 'Minute', 'Second']
    field = df[fieldName]
    for n in attr:
        df[temp+n] = getattr(field.dt, n.lower())
    df[temp+"Elapsed"] = field.astype(np.int64)
    if drop:
        df.drop(fieldName, axis =1, inplace = True)
        
def train_cats(df):
    '''
    Convert all string type columns to categorical(ordered)
    '''
    for n,c in df.items():
        if is_string_dtype(c):
            df[n] = c.astype("category").cat.as_ordered()

def apply_cats(df, target):
    '''
    sets the categories of df based on a target df
    '''
    for n,c in df.items():
        if n in target.columns and is_string_dtype(c):
            df[n] = df[n].astype("category").cat.as_ordered()
            df[n].cat.set_categories(target[n].cat.categories, ordered = True, inplace = True)

def show_missing_ratio(data, desc = False):
    if desc:
        display_all(data.isnull().sum().sort_values(ascending = False)/len(data))
    else:
        display_all(data.isnull().sum().sort_index()/len(data))

def fix_missing(df,n, c, na_dict):
    if is_numeric_dtype(c):
        if c.isnull().sum() or n in na_dict:
            df[n+"_na"] = c.isnull()
            if n not in na_dict:
                filler = c.median()
                na_dict[n] = filler
            df[n] = c.fillna(na_dict[n])
    return na_dict

def numericalize(df, n, c, max_n_cat):
    if not is_numeric_dtype(c) and len(c.cat.categories) > max_n_cat:
        df[n] = pd.Categorical(c).codes + 1

def get_sample(df,n):
    idxs = sorted(np.random.permutation(len(df))[:n])
    return df.iloc[idxs]


def proc_df(df, y_fld, na_dict = None, max_n_cat = 0, subset = None):
    '''
    splits dataframe into target variable and df
    converts the df into completely numerical data
    treats missing values by replacing with median and creating a column marking the missing value
    converts all categorical variables with less than max_n_cat categories into one hot encoded 
    the other categories are kept as label encoded
    
    if na_dict is given uses the dict to update the missing values
    '''
    if subset:
        df = get_sample(df, subset)
    ### separate y column
    if not is_numeric_dtype(df[y_fld]): df[y_fld].astype("category").cat.codes
    y = df[y_fld].values
    df.drop(y_fld, axis = 1, inplace = True)
    
    ##fix missing values
    if not na_dict:
        na_dict = {}
    for n,c in df.items():
        na_dict = fix_missing(df,n,c,na_dict)
        
    ## encoding categorical variables
    for n,c in df.items():
        numericalize(df, n, c, max_n_cat)
    df = pd.get_dummies(df)
    return [df, y,na_dict]

class Train_Test_Split():
    '''
    Divide data into train and test split based on type of data
    '''
    def __init__(self, data_type):
        self.data_type = data_type
    def _get_splitter(self):
        if self.data_type == "serial":
            return self.serial_splitter
        if self.data_type == "random":
            return random_splitter
    def serial_splitter(self, data, train_size):
        return data[:train_size], data[train_size:]
    def random_splitter(self, data, train_size):
        raise NotImplementedError

def draw_tree(t, df):
    plt.figure(figsize = (100,100))
    sklearn.tree.plot_tree(t, feature_names= df.columns, filled = True, rotate = True)
    

def var_summary(df, summary_fields, max_n_cat = 10):
    '''
    Create group wise average of various fields. 
    e.g. include mean, std, accuracy etc
    Use for identifying cases where model is performing badly
    '''
    categorical_feat = []
    for n,c in df.items():
        if is_categorical_dtype(c):
            if len(c.cat.categories) < max_n_cat:
                categorical_feat.append(n)
    for field in categorical_feat:
        print("############", field, "###############")
        print(df[field].value_counts())
        summary_fields.append(field)
        summ = df[summary_fields].groupby(field, as_index = False).mean()
        print(summ)
        summary_fields.pop()
        print("\n") 

def rf_feat_imp(m, df):
    feat = df.columns
    imp = np.round(m.feature_importances_,6)
    return pd.DataFrame({"feat":feat,"imp":imp}).sort_values("imp", ascending = False)

def plot_corr_dendogram(df):
    '''
    plot correlation dendogram using spearman correlation
    to be extended to use different distance measures
    '''
    corr = np.round(scipy.stats.spearmanr(df).correlation, 4)
    corr_condensed = hc.distance.squareform(1-corr)
    z = hc.linkage(corr_condensed, method='average')
    fig = plt.figure(figsize=(16,10))
    dendrogram = hc.dendrogram(z, labels=df.columns, orientation='left', leaf_font_size=16)
    plt.show()
