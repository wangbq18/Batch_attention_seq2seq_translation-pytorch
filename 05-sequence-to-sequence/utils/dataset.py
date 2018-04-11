import random
import re
import string
import unicodedata

import torch
from torch.utils.data import Dataset

SOS_token = 1
EOS_token = 2
MAX_LENGTH = 10

#词典类
class Lang(object):
    def __init__(self, name):
        self.name = name
        self.word2index = {'PAD':0,'SOS':1,'EOS':2}
        self.word2count = {}
        self.index2word = {0:"PAD",1: "SOS", 2: "EOS"}
        self.n_words = 3  # Count SOS and EOS

    def addSentence(self, sentence):
        for word in sentence.split(' '):
            self.addWord(word)

    def addWord(self, word):
        if word not in self.word2index:
            self.word2index[word] = self.n_words
            self.word2count[word] = 1
            self.index2word[self.n_words] = word
            self.n_words += 1
        else:
            self.word2count[word] += 1

#unicode转ascill码
def unicodeToAscii(s):
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn')


# Lowercase, trim, and remove non-letter characters

#转acsill码并去除标点符号
def normalizeString(s):
    s = unicodeToAscii(s.lower().strip())
    s = re.sub(r"([.!?])", r" \1", s)
    s = re.sub(r"[^a-zA-Z.!?]+", r" ", s)
    return s

#读取文件得到内容pairs，并建立两空字典
def readLangs(lang1, lang2, reverse=False):
    print("Reading lines...")

    # Read the file and split into lines
    lines = open('data/%s-%s.txt' % (lang1, lang2), encoding='utf-8').\
        read().strip().split('\n')

    # Split every line into pairs and normalize
    pairs = [[normalizeString(s) for s in l.split('\t')] for l in lines]

    # Reverse pairs, make Lang instances
    if reverse:
        pairs = [list(reversed(p)) for p in pairs]
        input_lang = Lang(lang2)
        output_lang = Lang(lang1)
    else:
        input_lang = Lang(lang1)
        output_lang = Lang(lang2)

    return input_lang, output_lang, pairs

#过滤规则
eng_prefixes = ("i am ", "i m ", "he is", "he s ", "she is", "she s",
                "you are", "you re ", "we are", "we re ", "they are",
                "they re ")

#过滤文件内容
def filterPair(p):
    return len(p[0].split(' ')) < MAX_LENGTH and \
        len(p[1].split(' ')) < MAX_LENGTH and \
        p[1].startswith(eng_prefixes)


def filterPairs(pairs):
    return [pair for pair in pairs if filterPair(pair)]

#准备数据，将内容pairs放入两哥字典
def prepareData(lang1, lang2, reverse=False):
    input_lang, output_lang, pairs = readLangs(lang1, lang2, reverse)
    print("Read %s sentence pairs" % len(pairs))
    pairs = filterPairs(pairs)
    print("Trimmed to %s sentence pairs" % len(pairs))
    print("Counting words...")
    for pair in pairs:
        input_lang.addSentence(pair[0])
        output_lang.addSentence(pair[1])
    print("Counted words:")
    print(input_lang.name, input_lang.n_words)
    print(output_lang.name, output_lang.n_words)
    print(random.choice(pairs))
    return input_lang, output_lang, pairs

#获得每句id序列
def indexesFromSentence(lang, sentence):
    return [lang.word2index[word] for word in sentence.split(' ')]

#添加末尾序列id并转化为longtensor
def tensorFromSentence(lang, sentence):
    indexes = indexesFromSentence(lang, sentence)
    indexes.append(EOS_token)
    result = torch.LongTensor(indexes)
    return result


def tensorFromPair(input_lang, output_lang, pair):#参数1：输入字典类    参数2：输出字典类     参数3：输入输出句子
    input_tensor = tensorFromSentence(input_lang, pair[0])
    target_tensor = tensorFromSentence(output_lang, pair[1])
    return input_tensor, target_tensor

#定义一个取数据类，重写了Dataset数据类
class TextDataset(Dataset):
    def __init__(self, dataload=prepareData, lang=['eng', 'fra']):
        self.input_lang, self.output_lang, self.pairs = dataload(
            lang[0], lang[1], reverse=True)
        self.input_all=[]
        self.output_all=[]
        self.mask=[]
        for pair in self.pairs:
            in_sen=pair[0]
            out_sen=pair[1]
            in_sen_id=[]
            out_sen_id=[]
            mask_sen=[]
            for word in in_sen.split(' '):
                in_sen_id.append(self.input_lang.word2index[word])
            in_sen_id.append(EOS_token)
            #填充
            if len(in_sen_id)<MAX_LENGTH:
                in_sen_id+=[0]*(MAX_LENGTH-len(in_sen_id))
            for word in out_sen.split(' '):
                out_sen_id.append(self.output_lang.word2index[word])
                mask_sen.append(1)
            out_sen_id.append(EOS_token)
            mask_sen.append(1)
            #填充
            if len(out_sen_id)<MAX_LENGTH:
                out_sen_id+=[0]*(MAX_LENGTH-len(out_sen_id))
            # 填充
            if (len(mask_sen)<MAX_LENGTH):
                mask_sen+=[0]*(MAX_LENGTH-len(mask_sen))
            self.input_all.append(in_sen_id)
            self.output_all.append(out_sen_id)
            self.mask.append(mask_sen)

        self.input_all=torch.LongTensor(self.input_all)
        self.output_all=torch.LongTensor(self.output_all)
        self.mask=torch.ByteTensor(self.mask)

        self.input_lang_words = self.input_lang.n_words
        self.output_lang_words = self.output_lang.n_words

    def __getitem__(self, index):
        # return tensorFromPair(self.input_lang, self.output_lang,self.pairs[index])#返回输入与输出句子的id序列
        return self.input_all[index],self.output_all[index],self.mask[index]
    def __len__(self):
        return len(self.pairs)
