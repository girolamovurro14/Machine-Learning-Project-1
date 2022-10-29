import sys
sys.path.append("../../ML_project1")

from loading_data import *
from preprocessing import *
from cleaning_dataset import *
from feature_engineering import *
from utilities_linear_regression import *
from utilities_logistic_regression import *
from postprocessing import *

##############################################################################

#%% Importing the train dataset and test dataset
train_original, col24_train = load_train_dataset()
test_original, col24_test = load_test_dataset()

#%% Splitting the dataset into 3 sub-datasets according to the categoric
# feature and deleting the constant features
train_datasets = split_jet(train_original, col24_train)
test_datasets = split_jet(test_original, col24_test)
# add the zero-columns for the prediction of the test set
for i in range(len(test_datasets)):
    n_rows = test_datasets[i][0][:,0].size
    col = np.zeros(n_rows)
    test_datasets[i][0] = np.insert(test_datasets[i][0], 1, col, axis=1)
#%%
index_list = [test_datasets[i][1] for i in range(len(test_datasets))]
    
#%% filling column 3
k_fold = 5
lambdas = np.logspace(-10, 0, 30)

train_filled = []
test_filled = []

for i in range(len(train_datasets)):
    train_jet_filled, test_jet_filled = feature_regression_col3(train_datasets[i][0], test_datasets[i][0], k_fold, lambdas, seed = 1)
    train_filled.append(train_jet_filled)
    test_filled.append(test_jet_filled)
    
#%% remove highly correlated columns

train_filled[0] = np.delete(train_filled[0], [4,5,8], 1)
train_filled[1] = np.delete(train_filled[1], [4,5,8,20], 1)
train_filled[2] = np.delete(train_filled[2], [4,8,11,30], 1)

test_filled[0] = np.delete(test_filled[0], [4,5,8], 1)
test_filled[1] = np.delete(test_filled[1], [4,5,8,20], 1)
test_filled[2] = np.delete(test_filled[2], [4,8,11,30], 1)
    

#%% cap the ouliers
train_out = []
test_out = []

for i in range(len(train_filled)):
    tr = fix_outliers(train_filled[i])
    train_out.append(tr)
    te = fix_outliers(test_filled[i])
    test_out.append(te)

#%% log tranform of the positive and skewned columns
indexes_skew = []
train_skew = []
test_skew = []
for i in range(len(train_out)):
    ind_train = ind_pos_neg(train_out[i])[0]
    ind_train[:2] = False
    tra = correct_skewness(train_out[i], ind_train)
    ind_test = ind_pos_neg(test_out[i])[0]
    ind_test[:2] = False
    tes = correct_skewness(test_out[i], ind_train)
    train_skew.append(tra)
    test_skew.append(tes) 
    
#%% cosine tranform of the angles
angle_cols0 = np.array([7, 10, 13, 15])
angle_cols1 = np.array([7, 10, 13, 15, 18])
angle_cols23 = np.array([10, 14, 17, 19, 23, 26])
to_correct = [angle_cols0, angle_cols1, angle_cols23]
train_angle = []
test_angle = []

for i in range(len(train_skew)):
    tr = cosine(train_skew[i], to_correct[i])
    te = cosine(test_skew[i], to_correct[i])
    train_angle.append(tr)
    test_angle.append(te)

#%% expansion with degree 7, 7, 7
train_exp = []
test_exp = []
best_degrees = []
degrees = np.array([1, 2, 3, 4, 5, 6, 7])
deg = 7
#%% lasts 8h
for i in range(len(train_angle)):
    ids, y, tx = split_into_ids_y_tx(train_angle[i])
    deg = best_degree_dataset(y, tx, degrees, k_fold, lambdas, seed = 1)[0]

#%%
for i in range(len(train_angle)):
    curr_exp_train = poly_expansion_blind(train_angle[i], deg)
    train_exp.append(curr_exp_train)
    curr_exp_test = poly_expansion_blind(test_angle[i], deg)
    test_exp.append(curr_exp_test)
    
#%% add coupled products
train_prod = []
test_prod = []

for i in range(len(train_angle)):
    tr = feature_cross_products(train_angle[i])
    te = feature_cross_products(test_angle[i])
    train_prod.append(np.c_[train_exp[i], tr])
    test_prod.append(np.c_[test_exp[i], te])
    
#%% add square root
train_sqrt = []
test_sqrt = []

for i in range(len(train_angle)):
    tr = squareroot(train_angle[i])
    te = squareroot(test_angle[i])
    train_sqrt.append(np.c_[train_prod[i], tr])
    test_sqrt.append(np.c_[test_prod[i], te])

#%% standardization
# notice that the very first feature is the offset, which is a constant column
# of ones, hence it cannot be standardized
train_stand = []
test_stand = []
for i in range(len(train_prod)):
    curr_train, curr_mean, curr_std = standardize_train(train_prod[i])
    curr_train[:,2] = 1
    curr_test = standardize_test(test_prod[i], curr_mean, curr_std)
    curr_test[:,2] = 1
    train_stand.append(curr_train)
    test_stand.append(curr_test)    

#%% LINEAR polynomial expansion of the dataset
expanded_train = []
expanded_test = []
deg_sel_train = []
degrees = np.arange(1,8)

# polinomial expansion of the train set
for i in range(len(train_stand)):
    curr_expansion, deg_sel = poly_expansion_lin(train_stand[i], degrees, k_fold, lambdas, seed = 1)
    expanded_train.append(curr_expansion)
    deg_sel_train.append(deg_sel)
# polinomial expansion of the test set with the corresponding degree of the train
for i in range(len(test_stand)):
    curr_expansion = poly_expansion_blind_degrees(test_stand[i], deg_sel_train[i])
    expanded_test.append(curr_expansion)
    deg_sel_train.append(deg_sel)

#%% RIDGE REGRESSION
ws = []
lambdas = np.logspace(-10, 0, 30)
k_fold = 10
lamb = []

for i in range(len(train_stand)):
    ids, y, tx = split_into_ids_y_tx(train_stand[i])
    l = cross_validation_demo_tx_lin(y, tx, k_fold, lambdas)[0]
    lamb.append(l)
    w = ridge_regression(y, tx, l)[0]
    ws.append(w)
    
#%% compute the predictions
ys = generate_linear_prediction(test_stand, ws)

#%% compute the optimal threshold for each sub-dataset
vec_thresholds = np.linspace(-2, 2, 101)
thresholds = []
for i in range(len(train_stand)):
    thr = optimal_threshold(train_stand[i], vec_thresholds, lamb[i])
    thresholds.append(thr)

#%% compute predictions according to the selected threshold
prediction = collect(ys, index_list, thresholds)

#%% generate the submission
generate_csv(prediction, test_original[:,0], "sample_submission_dm.csv")

