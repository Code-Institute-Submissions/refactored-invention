import os
import sys
import logging
from flask import Flask, render_template, redirect, request, jsonify
import json
import requests
import music
from random import randint, random
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from collections import OrderedDict
from operator import itemgetter

app = Flask(__name__)

# error logging
logging.basicConfig(filename='log/guess_next_line.log',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger=logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

# list of video ids that have lyrics provided by musixmatch
pre_canned_videoId = ['YQHsXMglC9A','0-EF60neguk','MN3x-kAbgFU','YR5ApYxkU-U','n4RjJKxsamQ','raNGeq3_DtM','TvnYmWpD_T8','x5GuBa4Bbnw','4YR_Mft7yIM','JJAXwAaA2w','u1xrNaTO1bI','jhdFe3evXpk','YQHsXMglC9A']

def levestein_score(to_be_scored_string, answer):
    return fuzz.ratio(to_be_scored_string, answer)

def search_from_file(filename, search_term,search_type):
    """Handle the process of searching for data in a file"""
    with open(filename, "r") as searchfile:
        if search_type == 0:
            for line in searchfile:
                if search_term in line:
                    return line.rstrip()
        elif search_type == 1:
            file_lines = {}
            for num, line in enumerate(searchfile, 0):
                if search_term in line:
                    file_lines[num] = line.rstrip()
            return file_lines if any(file_lines.values()) else None

def read_from_file(filename):
    """Handle the process of reading data from a file"""
    file_lines = dict()
    with open(filename, "r") as readfile:
        for num, line in enumerate(readfile, 0):
            file_lines[num] = line.rstrip()
        return file_lines

def update_file(filename, update_term, write_value):
    """Handle the process of updating data in a file"""

    data = update_term + "," + write_value

    with open(filename + ".w", "w") as outFile:

        with open(filename, "r") as inputfile:
            for line in inputfile:

                if update_term in line:
                    outFile.writelines("{}\n".format(data.rstrip()))
                else:
                    outFile.writelines("{}\n".format(line.rstrip()))
    os.rename(filename + ".w", filename)


def write_to_file(filename, data):
    """Handle the process of writing data to a file"""
    with open(filename, "a") as file:
        file.writelines("{}\n".format(data))

def generate_leaderboard(leaderboard_length):

    class_list = ['bg-primary','bg-warning','bg-success','bg-danger']

    all_players = read_from_file('data/players.txt')

    names_dict = {}

    names = []

    result = []

    # check for empty players file and return placeholder values for template display without further processing
    if ( len(list(all_players.values()) ) == 0):

        names = ["Log in to join the fun"]
        result = ["<li>No Completed Song Scores</li>"]

        return [names,class_list,result]

    # create a list of all players names

    for name in list(all_players.values()):

        name_array = name.split(",")

        names_dict[name_array[0]] = int(name_array[1])

        names = list(OrderedDict(sorted(names_dict.items(), key = itemgetter(1), reverse = True)).keys())

    for name in names:
        # select all songs by person, if no songs 'None' is returned
        raw_result = search_from_file('data/song_scores.txt', name,1) # 0 returns the first result, 1 returns all results

        if ( raw_result is not None ):
            string = ""
            for key, value in raw_result.items():
                string += "<li>{0} - {1}</li>".format(value.split(",")[1],value.split(",")[2])
            result.append(string)
        else:
            result.append('<li>No Completed Song Scores</li>')

    # create list of classes which is longer than the names, extra is ignored in the template
    classes = class_list * (len(names))

    # print(names)
    # print(classes)
    # print(result)

    # if called with the same number of names in the song score file return all available names
    if ( leaderboard_length >= len(names) ):
        return [names,classes,result]
    elif ( leaderboard_length == 0 ):
        return [names,classes,result]
    else:
    # if called with less than the number of names in the song score file return then number requested
        return [names[:leaderboard_length],classes[:leaderboard_length],result[:leaderboard_length]]


@app.route('/', methods=['GET'])
def index():
    if request.method == "GET":

        # This API request is being bypassed due to the chance that video id's returned are not music videos or are music videos but the lyrics are not available
        # If this project was to be made into a live service a library would have to be constructed of vidoes with lyrics by videoCategory

        '''
        payload = {'part': 'snippet', 'key': 'AIzaSyDBJyenwpSZ3BFota9_w0aueB2lj9fnl1M', 'chart': 'mostPopular' ,'maxResults': 10, 'videoCategory': '10'}
        l = requests.Session().get('https://www.googleapis.com/youtube/v3/videos', params=payload)
        resp_dict = json.loads(l.content)
        ytVideoId = resp_dict['items'][0]['id']
        print(resp_dict['items'][0]['id'])
        for i in range(len(resp_dict['items'])):
            print(resp_dict['items'][i]['id'])
        '''

        randomNumber = randint(0,len(pre_canned_videoId)- 1)

        try:

            rawlyric = music.fetch_srt('xxx',pre_canned_videoId[randomNumber])

            lyric = music.convert_srt(rawlyric)

            return render_template("index.html", page_title="Home", value=pre_canned_videoId[randomNumber],lyrics=lyric)

        except Exception as err:
            logger.error(err)
            return render_template('500.html'), 500

@app.route('/evaluate_answer', methods=['POST'])
def evaluate_answer():
    if request.method == "POST":
        data = json.loads(request.data) # load JSON data from request

        score = str(levestein_score(data['lyricAnswer'],data['stringToBeEvaluated']))
        return_data = {"score": score}

        response = app.response_class(
            response=json.dumps(return_data),
            status=200,
            mimetype='application/json'
        )
        return response

@app.route('/update_score', methods=['POST'])
def update_score():
    if request.method == "POST":
        data = json.loads(request.data) # load JSON data from request

        update_file('data/players.txt', data['writeData'][0], data['writeData'][1])

        response = app.response_class(
            status=200,
            mimetype='application/json'
        )
        return response

@app.route('/song_score', methods=['POST'])
def song_total_score():
    if request.method == "POST":
        data = json.loads(request.data) # load JSON data from request

        write_to_file('data/song_scores.txt',data['writeData']);

        response = app.response_class(
            status=200,
            mimetype='application/json'
        )
        return response


@app.route('/login', methods=['POST'])
def login():
    if request.method == "POST":
        data = json.loads(request.data) # load JSON data from request

        result = search_from_file('data/players.txt',data['userName'],0)

        if (result):

            return_data = result.split(',')

        else:

            write_to_file('data/players.txt',data['userName'] + ',0')

            return_data = [data['userName'],0]

        response = app.response_class(
            response=json.dumps({'user_name':return_data[0], 'total_score':return_data[1]}),
            status=200,
            mimetype='application/json'
        )

        return response

@app.route('/all_players')
def all_players():
    return render_template("all_players.html")

@app.route('/leaderboard')
def leaderboard():

    template_values = generate_leaderboard(0) # 0 option provides full results, called with interger option

    return render_template("leaderboard.html", names_classes=zip(template_values[0],template_values[1],template_values[2]))

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception


if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            debug=True)
