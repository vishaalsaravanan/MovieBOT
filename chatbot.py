#Data Pre Processing 
import numpy as np
import re 
import time

import tensorflow.compat.v1 as tf

tf.disable_v2_behavior() 

lines=open('movie_lines.txt',errors='ignore',encoding='utf-8').read().split('\n')
conversations=open('movie_conversations.txt',errors='ignore',encoding='utf-8').read().split('\n')

#********************Data Preprocessing********************************** 
#creating a Dictionary!
id2line={}
for line in lines:
    line_=line.split(' +++$+++ ')
    if len(line_)==5:
        id2line[line_[0]]=line_[4]
        
#Creating the list of all of the conversations
conversations_ids=[]
for conversation in conversations[:-1]:
    _conversation= conversation.split(' +++$+++ ')[-1][1:-1].replace("'","").replace(" ","")
    #[takes the last element][exclude []]
    conversations_ids.append(_conversation.split(','))
    
#Getting the questions and the answers
questions =[]
answers=[]
for conversation in conversations_ids:
    for i in range(len(conversation)-1):
        questions.append(id2line[conversation[i]])
        answers.append(id2line[conversation[i+1]])
        
#Cleaning of the texts first
def clean_text(text):
    text=text.lower()
    text=re.sub(r"i'm","i am",text)
    text=re.sub(r"he's","he is",text)
    text=re.sub(r"that's","that is",text)
    text=re.sub(r"she's","she is",text)
    text=re.sub(r"what's","what is",text)
    text=re.sub(r"where's","what is",text)
    text=re.sub(r"\'ll"," will",text)
    text=re.sub(r"\'ve"," have",text)
    text=re.sub(r"\'re"," are",text)
    text=re.sub(r"\'d"," would",text)
    text=re.sub(r"\'won't","will not",text)
    text=re.sub(r"\'can't","cannot",text)
    text=re.sub(r"[-()\"#/@:;<>{}+=~|.?,]","",text)
    return text
    
#Cleaned Questions
clean_questions=[]
for question in questions:
    clean_questions.append(clean_text(question))   

#Cleaned Answers    
clean_answers=[]
for answer in answers:
    clean_answers.append(clean_text(answer))   
    
#Create a dictionary that maps each word to its number of occurences.
word2count={}
for question in clean_questions:
    for word in question.split():
        if(word not in word2count):
            word2count[word]=1
        else:
            word2count[word]+=1
        
for answer in clean_answers:
    for word in answer.split():
        if(word not in word2count):
            word2count[word]=1
        else:
            word2count[word]+=1
#Creating two dictionaries that map the questions words and the answers words to a unique integer
threshold=20
questionswords2int={}
word_number=0
for word,count in word2count.items():
    if(count>=threshold):
        questionswords2int[word]=word_number
        word_number+=1
answerswords2int={}
word_number=0
for word,count in word2count.items():
    if(count>=threshold):
        answerswords2int[word]=word_number
        word_number+=1
        
#Adding the last tokens to these two dictionaries
tokens=['<PAD>','<EOS>','<OUT>','<SOS>']
for token in tokens:
    questionswords2int[token]=len(questionswords2int)+1
for token in tokens:
    answerswords2int[token]=len(answerswords2int)+1
    
#Creating the inverse dictionary of the answersword2int dictionary
answersint2word={w_i:w for w,w_i in  answerswords2int.items()}

#Adding the End of the String to the every answer
for i in range(len(clean_answers)):
    clean_answers[i]+=' <EOS>'
    
#Translating all the questions and answers into integers
#and replacing all the words that were filterd out by <OUT>
questions_into_int = []
for question in clean_questions:
    ints=[]
    for word in question.split():
        if word not in questionswords2int:
            ints.append(questionswords2int['<OUT>'])
        else:
             ints.append(questionswords2int[word])
    questions_into_int.append(ints)

answers_into_int = []    
for question in clean_questions:
    ints=[]
    for word in answer.split():
        if(word not in answerswords2int):
            ints.append(answerswords2int['<OUT>'])
        else:
             ints.append(answerswords2int[word])
    answers_into_int.append(ints)
    
#Sorting questions and answers by length of questions
sorted_clean_questions=[]
sorted_clean_answers=[]
for length in range(1,25+1):
    for i in enumerate(questions_into_int):
        if len(i[1])==length:
               sorted_clean_questions.append(questions_into_int[i[0]])
               sorted_clean_answers.append(answers_into_int[i[0]])
               
               
#**********Building the Seq2Seq Model*****************************************
#Creating placeholders for the inputs and the targets.
def model_inputs():
    inputs=tf.placeholder(tf.int32,[None,None],name='input')
    targets=tf.placeholder(tf.int32,[None,None],name='target')
    lr=tf.placeholder(tf.float32,name='learning_rate')
    keep_prob=tf.placeholder(tf.float32,name='keep_prob')#for controlling dropout rates
    return inputs,targets,lr,keep_prob

#Preprocessing the targets.
def preprocess_targets(targets,word2int,batch_size):
    left_side=tf.fill([batch_size,1],word2int['<SOS>'])
    right_side=tf.strided_slice(targets,[0,0],[batch_size,-1],[1,1])
    preprocessed_targets=tf.concat([left_side,right_side],1)
    return preprocessed_targets
      
#Creating the Encoder RNN layer.
def encoder_rnn(rnn_inputs,rnn_size,num_layers,keep_prob,sequence_length):  
    #rnn_size =size of input sensors
    # lstm=tf.contrib.rnn.BasicLSTMCell(rnn_size)
    # lstm_dropout=tf.contrib.rnn.DropoutWrapper(lstm,input_keep_prob=keep_prob)
    # encoder_cell=tf.contrib.rnn.MultiRNNCell([lstm_dropout]*num_layers)
    # _,encoder_state=tf.nn.bidirectional_dynamic_rnn(cell_fw=encoder_cell,
    #                                                 cell_bw=encoder_cell,
    #                                                 sequence_length=sequence_length,
    #                                                 inputs=rnn_inputs,
    #                                                 dtype=tf.float32)#forward=backward.
    lstm=tf.layers.rnn.BasicLSTMCell(rnn_size)
    lstm_dropout=tf.layers.rnn.DropoutWrapper(lstm,input_keep_prob=keep_prob)
    encoder_cell=tf.layers.rnn.MultiRNNCell([lstm_dropout]*num_layers)
    _,encoder_state=tf.nn.bidirectional_dynamic_rnn(cell_fw=encoder_cell,
                                                    cell_bw=encoder_cell,
                                                    sequence_length=sequence_length,
                                                    inputs=rnn_inputs,
                                                    dtype=tf.float32)#forward=backward.
    return encoder_state 
    
#Decoding the training Set
def decode_training_state(encoder_state,decoder_cell,decoder_embeded_input,
                          sequence_length,decoding_scope,output_function,keep_prob,batch_size):
    #Encoder state returned from the encoder.
    #decoding scope-Advance tensorflow datastructue for wrapping tensorflow variables.
    attention_states=tf.zeros([batch_size,1,decoder_cell.output_size])
    attention_keys,attention_values,attention_score_function,attention_construct_function=tf.contrib.Seq2Seq.prepare_attention(
        attention_states,
        attention_option='bahdanu',
        num_units=decoder_cell.output_size)
    
    #attention_keys->keys to be compared with target size!
    #attention_values->To prepare the context vector!
    #attention_score_function->to be compare the similarity between the keys and target 
    #attention_construct_function->to be used for constructing the attention state
    training_decoder_function=tf.contrib.Seq2Seq.attention_decoder_fn_train(
                                                                             encoder_state[0],
                                                                             attention_keys,
                                                                             attention_values,
                                                                             attention_score_function,
                                                                             attention_construct_function,
                                                                             name="attn_dec_train")
    #training_decoder_function for building the decoding dynamic rnn.
    decoder_output,decoder_final_state,decoder_final_context_state=tf.contrib.Seq2Seq.dynamic_rnn_decoder(
                                                                    decoder_cell,
                                                                    training_decoder_function,
                                                                    decoder_embeded_input,
                                                                    sequence_length,
                                                                    scope=decoding_scope)
    decoder_output_dropout=tf.nn.dropout(decoder_output,
                                         keep_prob)
    return output_function(decoder_output_dropout)
    
#Decoding the Test/Validation Set 
def decode_test_state(encoder_state,decoder_cell,decoder_embededdings_matrix,
                          sos_id,eos_id,maximum_length,num_words,
                          sequence_length,decoding_scope,output_function,keep_prob,batch_size):
    #Encoder state returned from the encoder !.
    #maximum_lenght-Maximum length of a longest answer !.
    #num_words=Number of answers in the dictionary!.
    #decoding scope-Advance tensorflow datastructue for wrapping tensorflow variables !..
    attention_states=tf.zeros([batch_size,1,decoder_cell.output_size])
    attention_keys,attention_values,attention_score_function,attention_construct_function=tf.contrib.Seq2Seq.prepare_attention(
        attention_states,
        attention_option='bahdanu',
        num_units=decoder_cell.output_size)
    
    #attention_keys->keys to be compared with target size!
    #attention_values->To prepare the context vector!
    #attention_score_function->to be compare the similarity between the keys and target 
    #attention_construct_function->to be used for constructing the attention state
    test_decoder_function=tf.contrib.Seq2Seq.attention_decoder_fn_inference( output_function,
                                                                             encoder_state[0],
                                                                             attention_keys,
                                                                             attention_values,
                                                                             attention_score_function,
                                                                             attention_construct_function,
                                                                             decoder_embededdings_matrix,
                                                                             sos_id,
                                                                             eos_id,
                                                                             maximum_length,
                                                                             num_words,
                                                                             name="attn_dec_inf")
    #name-Scope Name/Checking which mode our decoder is in
    #training_decoder_function for building the decoding dynamic rnn.
    test_predictions,decoder_final_state,decoder_final_context_state=tf.contrib.Seq2Seq.dynamic_rnn_decoder(
                                                                    decoder_cell,
                                                                    test_decoder_function,
                                                                    scope=decoding_scope)
    #test_predictions=decoder output
    return test_predictions

def decoder_rnn(decoder_embeded_input,
                decoder_embededdings_matrix,
                encoder_state,
                num_words,
                sequence_length,
                rnn_size,
                num_layers,
                word2int,
                keep_prob,
                batch_size
                ):
   with tf.variable_scope('decoding') as decoding_scope:
       lstm=tf.contrib.rnn.BasicLSTMCell(rnn_size)
       lstm_dropout=tf.contrib.rnn.DropoutWrapper(lstm,input_keep_prob=keep_prob)
       decoder_cell=tf.contrib.rnn.MultiRNNCell([lstm_dropout]*num_layers)
       weights=tf.truncated_normal_intializer(stddev=0.1)
       biases=tf.zeros_initializer()
       output_function=lambda x:tf.contrib.layers.fully_connected(x,
                                                                  num_words,
                                                                  None,
                                                                  scope=decoding_scope,
                                                                  weights_initializer=weights,
                                                                  biases_initializer=biases)
       #3rd arg-Activation Function,default function will be relu
       training_predictions=decode_training_state(encoder_state, 
                                               decoder_cell, 
                                               decoder_embeded_input, 
                                               sequence_length, 
                                               decoding_scope, 
                                               output_function, 
                                               keep_prob,
                                               batch_size)
       decoding_scope.reuse_variables()
       test_predictions=decode_test_state(encoder_state, 
                                          decoder_cell, 
                                          decoder_embededdings_matrix, 
                                          word2int['<SOS>'], 
                                          word2int['<EOS>'], 
                                          sequence_length-1, 
                                          num_words, 
                                          sequence_length, 
                                          decoding_scope, 
                                          output_function,
                                          keep_prob, 
                                          batch_size)
       
       return training_predictions,test_predictions
   
#Building Seq2Seq model
def seq2seq_model(inputs,
                  targets,
                  keep_prob,
                  batch_size,
                  sequence_length,
                  answers_num_words,
                  questions_num_words,
                  encoder_embedding_size,
                  decoder_embedding_size,
                  rnn_size,
                  num_layers,
                  questionswords2int):
    
    # encoder_embedded_input=tf.contrib.layers.embed_sequence(inputs,
    #                                                         answers_num_words+1,
    #                                                         encoder_embedding_size,
    #   
        #                                              intializer=tf.random_uniform_initializer(0,1))

    encoder_embedded_input=tf.keras.layers.Embedding( inputs,
                                                      encoder_embedding_size,
                                                      embeddings_initializer=tf.random_uniform_initializer(0,1))
  
    encoder_state=encoder_rnn(encoder_embedded_input, 
                              rnn_size, 
                              num_layers, 
                              keep_prob, 
                              sequence_length)
    preprocessed_targets=preprocess_targets(targets, questionswords2int, batch_size)
    decoder_embedding_matrix=tf.Variable(tf.random_uniform([questions_num_words+1,decoder_embedding_size],0,1))
    decoder_embedded_input=tf.nn.embedding_lookup(decoder_embedding_matrix,preprocessed_targets)
    training_predictions,test_predictions=decoder_rnn(decoder_embedded_input,
                                                      decoder_embedding_matrix,
                                                      encoder_state,
                                                      questions_num_words,
                                                      sequence_length,
                                                      rnn_size,
                                                      num_layers,
                                                      questionswords2int,
                                                      keep_prob,
                                                      batch_size)  
    
    return training_predictions,test_predictions
    
#***********************************Training the SEQ2SEQ MOdel**********************  
#Setting the hyperparameters
epochs=75
batch_size=64
rnn_size=512
num_layers=3
encoding_embedding_size=512#512 columns
decoding_embedding_size=512  
learning_rate=0.01
learning_rate_decay=0.90   
min_learning_rate=0.0001
keep_probability=0.5#drop 50 % of the nodes each time in the hidden layer
    
#Defining a session
tf.reset_default_graph()
session=tf.InteractiveSession()

#Loading the model inputs 
inputs,targets,lr,keep_prob=model_inputs()

#Setting the Sequence length
sequence_length=tf.placeholder_with_default(25,None,name="sequence_length")

#Getting the shape of the input tensor
input_shape=tf.shape(inputs)
    
#Getting the test and training predictions
training_predictions,test_predictions=seq2seq_model(tf.reverse(inputs,[-1]),
                                                    targets,
                                                    keep_prob,
                                                    batch_size,
                                                    sequence_length,
                                                    len(answersint2word),
                                                    len(questionswords2int),
                                                    encoding_embedding_size,
                                                    decoding_embedding_size,
                                                    rnn_size,
                                                    num_layers,
                                                    questionswords2int)

    
    
    
    
    
    
    