import requests
from bs4 import BeautifulSoup
import nltk
from textblob import TextBlob
from quantulum3 import parser
import re
import warnings
import spacy
from spacy.symbols import *
from spacy.matcher import Matcher
from spacy.tokens import Span
from nltk.tokenize import word_tokenize
from PyDictionary import PyDictionary
import copy
import logging
import random

logging.getLogger("quantulum3").setLevel(logging.CRITICAL)

nltk.download('punkt', quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("brown", quiet=True)
warnings.simplefilter('ignore')

headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '3600',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
}

# use BeautifulSoup and requests to inspect url HTML
def parse_url(url):
    req = requests.get(url, headers)
    soup = BeautifulSoup(req.content, 'html.parser')

    title = soup.find("h1" , class_="headline heading-content").get_text().lstrip().rstrip()

    ingredient_spans = soup.find_all('span' , class_='ingredients-item-name')
    ingredients = []
    for span in ingredient_spans:
        ingredient = span.get_text().lstrip().rstrip()
        ingredients.append(ingredient)

    instructions_ul = soup.find_all("li" , class_="subcontainer instructions-section-item")
    instructions = []
    for step in instructions_ul:
        instructions.append(step.find("div" , class_="paragraph").get_text().lstrip().rstrip())

    ingredients_dict,ingredients_lst = get_ingredients(ingredients)
    tools_list = get_tools(instructions, ingredients_dict, title)
    methods_list = get_methods(instructions)

    original_ingredients = copy.deepcopy(ingredients_dict)
    original_instructions = copy.deepcopy(instructions)

    return ingredients_dict,tools_list,methods_list,instructions

# either doubles or halves the ingredients depending on the factor passed in (2.0 or 0.5)
def double_half_ingredients(ingredients_dict, factor):
    converted_ingredients = {}

    for k in ingredients_dict.keys():
        measurement = ingredients_dict[k]
        quantities = re.findall('\d*\.?\d+', measurement)

        new_measurement = measurement
        for q in quantities:
            new_q = float(q) * factor

            new_measurement = new_measurement.replace(q, str(new_q))

        converted_ingredients[k] = new_measurement

    return converted_ingredients

#takes list of ingredients with measurements. Return dictionary with ingredient and measurement
def get_ingredients(lst):
    all = {}
    ingredient_lst = []
    for ingredient in lst:
        quants = parser.parse(ingredient)
        measurement = ""
        if len(quants) == 0:
            all[ingredient] = ""
            ingredient_lst.append(ingredient)
            continue
        if len(quants) == 2 and str(quants[0].unit) == "" and quants[1].value < 1:
            measurement = measurement + str(quants[0].value + quants[1].value)
            measurement = measurement + " " + str(quants[1].unit)
        elif len(quants) == 2 and str(quants[0].unit) == "" and quants[1].value > 1:
            measurement = str(quants[1].value * quants[0].value) + " " + str(quants[1].unit)
        else:
            measurement = str(quants[0].value) + " "+ str(quants[0].unit)

        #delete measurements
        for quant in quants:
            ingredient = ingredient.replace(quant.surface,"")

        blob = TextBlob(ingredient)

        if len(blob.noun_phrases) == 0:
            all[str(blob).lstrip()] = measurement
            ingredient_lst.append(str(blob).lstrip())
        elif len(blob.noun_phrases) == 1:
            all[blob.noun_phrases[0].lstrip()] = measurement
            noun_list = str(blob.noun_phrases[0].lstrip()).split(" ")
            for noun in noun_list:
                ingredient_lst.append(noun)

    return all, ingredient_lst

#helper function for get_tools
def strip_preps(np):
    badTags = ["DT", "PRP$"]
    npStr = ""
    for word in np:
        if word.tag_ not in badTags:
            if word.text == "-":
                npStr = npStr[:-1] + "-"
            else:
                npStr += word.text + " "
    return npStr[:-1]

def get_np(instruction):
    pattern_single = [
        {'TAG': 'VB', 'OP': '+'},
        {'TAG': "IN", 'OP': '?'},
        {'TAG': "DT", 'OP': '?'},
        {'TAG': 'NN', 'OP': '*'},
        {'TAG': 'NN', 'OP': '+'}
    ]
    pattern_plural = [
        {'TAG': 'VB', 'OP': '+'},
        {'TAG': "IN", 'OP': '?'},
        {'TAG': "DT", 'OP': '?'},
        {'TAG': 'NN', 'OP': '*'},
        {'TAG': 'NNS', 'OP': '+'}
    ]

    patterns = [pattern_single, pattern_plural]
    doc = nlp(instruction)
    verb_phrases = set()

    for pattern in patterns:
        matcher = Matcher(nlp.vocab)
        matcher.add("verb-phrases", None, pattern)
        matches = matcher(doc)

        [verb_phrases.add(doc[start:end].text.lower()) for _, start, end in matches]

    if not verb_phrases:
        lastToken = doc[len(doc)-1:len(doc)]
        if lastToken[0].text == "?":
            lastToken = doc[len(doc)-2:len(doc)-1]
        if lastToken[0].tag_ == "VB":
            verb_phrases.add(lastToken[0].text)

    vp_list = list(verb_phrases)
    random.shuffle(vp_list)

    return vp_list

#takes instructions, ingredients dictionary, and title. Returns list of possible tools
def get_tools(lst, ingredients, title):
    ingr = set()
    noun_phrases = set()
    ingrsList = list(ingredients.keys())
    ingrsList = [x.replace(",", "").replace("-", " ") for x in ingrsList]
    goodWords = ["used for", "used to", "utensil", "tool"]

    [ingr.add(word.lower()) for sent in ingrsList for word in sent.split(" ")]
    [ingr.add(word.lower()) for word in title.split(" ")]

    for step in lst:
        doc = nlp(step)
        nps = []
        for np in doc.noun_chunks:
            words = np.text.replace(",", "").split(" ")
            flag = False
            for w in words:
                if w in ingr or re.search('\d', w) or re.search('[A-Z]+[a-z]+$', w):
                    flag = True
                    break
            if not flag:
                nps.append(np)
        [noun_phrases.add(strip_preps(x)) for x in nps]

    noun_dict = {}

    for key in noun_phrases:
        noun_dict[key] = set(key.split(" "))

    for np in noun_dict.keys():
        np_set = set(np.split(" "))

        for np1 in noun_dict.keys():
            if np_set != noun_dict[np1]:
                common_set = np_set & noun_dict[np1]
                if common_set != set():
                    if np in noun_phrases:
                        noun_phrases.remove(np)
                    if np1 in noun_phrases:
                        noun_phrases.remove(np1)
                    noun_phrases.add(' '.join([word for word in np.split(" ") if word in common_set]))

        for i in ingrsList:
            if np in i and i in noun_phrases:
                noun_phrases.remove(i)

    dictionary=PyDictionary()
    np_temp = set(noun_phrases)

    for np in np_temp:
        wordSplit = np.split(" ")
        word = np.split(" ")[-1]
        meaningsDict = dictionary.meaning(word, disable_errors=True)
        if meaningsDict:
            if 'Noun' in meaningsDict.keys():
                meaningsNoun = meaningsDict['Noun']
                flag = [True for m in meaningsNoun for gw in goodWords if gw in m]
                if flag == []:
                    noun_phrases.remove(np)
            else:
                noun_phrases.remove(np)
        else:
            noun_phrases.remove(np)

    return [x for x in noun_phrases if len(x) > 1]

#takes instructions, returns list of verbs
def get_methods(steps):
    verbs = {}
    badWords = ["let", "serve", "bring", "place", "be", "make", "use", "read", "turn", "add", "remove", "move", "create", "begin", "allow", "continue"]
    pattern=[{'TAG': 'VB'}]

    matcher = Matcher(nlp.vocab)
    matcher.add("verb-phrases", None, pattern)

    for step in steps:
        doc = nlp(step)
        matches = matcher(doc)
        tempVerbs = [doc[start:end].text.lower() for _, start, end in matches]
        for v in tempVerbs:
            if v not in badWords:
                if v not in verbs.keys():
                    verbs[v] = 1
                else:
                    verbs[v] += 1

    verbs = dict(sorted(verbs.items(), key=lambda item: item[1], reverse=True))
    verbs = list(verbs.keys())
    verbs[0] += " (primary)"

    return verbs

# read in the allrecipes.com url -> SAMPLE URL TO TEST: https://www.allrecipes.com/recipe/280509/stuffed-french-onion-chicken-meatballs/
def read_in_url():
    recipe_url = input('Please input a url from allrecipes.com: ')

    parse_url(recipe_url)

def printer(title,ingredients_dict,instructions_lst,tools,methods):
    print(title)
    print("Ingredients:")
    for k in ingredients_dict.keys():
        print("\t"+k+": "+ingredients_dict[k])
    print("Tools:")
    for t in tools:
        print("\t" + t)
    print("Methods:")
    for m in methods:
        print("\t" + m)
    print("Instructions:")
    for i,instruction in enumerate(instructions_lst):
        print("\tStep " + str(i+1)+": "+instruction)

#takes ingredients dictionary and replace meat and fish with veggies. Return new dictionary
def veg_replace(dic,instructions, make_veg):

    if make_veg:

        meats= ['bacon bits', 'chicken','wings', 'beef', 'ground beef', 'duck', 'pork', 'ham','prosciutto', 'fish', 'sea bass', 'tilapia', 'salmon', 'halibut', 'trout','flounder',
        'turkey', 'meat stock', 'liver', 'crab', 'shrimp', 'liver', 'bacon', 'lamb','steak' ]
        meat_substitutes = {'bacon bits':'tofu', 'chicken': 'eggplant', 'wings': 'eggplant', 'beef': 'tofu', 'ground beef': 'lentils',
                            'duck': 'tempeh', 'pork': 'seitan', 'ham': 'jackfruit',
                            'prosciutto': 'mushroom', 'fish': 'tofu', 'sea bass': 'cauliflower', 'tilapia': 'seitan',
                            'salmon': 'eggplant', 'halibut': 'tempeh', 'trout': 'tofu', 'flounder': 'jackfruit',
                            'turkey': 'seitan', 'meat stock': 'vegetable stock',
                            'crab': 'cauliflower', 'shrimp': 'tofu', 'liver': 'tempeh', 'bacon': 'fried shallots',
                            'lamb': 'eggplant','steak':'tofu'}

        substitutions = 0

        deleting_ing = []
        deleted_map = {}
        for ing in dic.keys():
            tokens = word_tokenize(ing)
            for token in tokens:
                if token in meats:
                    deleting_ing.append(ing)
                    substitutions += 1


        for ing in deleting_ing:
            if ing in dic.keys():
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in meat_substitutes.keys():
                        dic[meat_substitutes[token]] = dic[ing]

                        deleted_map[ing] = meat_substitutes[token]
                del dic[ing]

        for i,instruction in enumerate(instructions):
            for ing in deleting_ing:
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in instruction:
                        if token in meat_substitutes.keys():
                            instructions[i] = instruction.replace(token,meat_substitutes[token])
                        else:
                            for old_ing in deleted_map.keys():
                                if token in old_ing:
                                    instructions[i] = instruction.replace(old_ing, deleted_map[old_ing])

        if substitutions == 0:
            dic['kale'] = '2 pieces'
            instructions.append("Top with kale.")

        return dic,instructions

    else:

        meat_substitutes = {'eggplant',  'tofu', 'lentils',
                            'tempeh', 'seitan', 'jackfruit',
                            'mushroom', 'tofu', 'cauliflower',
                            'vegetable stock', 'fried shallots', 'kale'}

        meats = {'eggplant': 'wings', 'tofu': 'beef', 'lentils': 'ground beef', 'tempeh': 'duck',
                            'seitan': 'pork', 'jackfruit': 'ham', 'mushroom': 'prosciutto',
                            'tofu': 'fish', 'cauliflower': 'shrimp', 'vegetable stock': 'beef stock', 'fried shallots': 'bacon', 'kale':'prosciutto'}

        substitutions = 0
        deleting_ing = []
        deleted_map = {}
        for ing in dic.keys():
            tokens = word_tokenize(ing)
            for token in tokens:
                if token in meat_substitutes:
                    deleting_ing.append(ing)
                    substitutions += 1

        for ing in deleting_ing:
            if ing in dic.keys():
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in meats.keys():
                        dic[meats[token]] = dic[ing]

                        deleted_map[ing] = meats[token]
                del dic[ing]

        for i,instruction in enumerate(instructions):
            for ing in deleting_ing:
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in instruction:
                        if token in meats.keys():
                            instructions[i] = instruction.replace(token,meats[token])
                        else:
                            for old_ing in deleted_map.keys():
                                if token in old_ing:
                                    instructions[i] = instruction.replace(token, deleted_map[old_ing])


        if substitutions == 0:
            dic['bacon bits'] = '1 teaspoon'
            instructions.append("Sprinkle bacon bits on dish.")

        return dic,instructions

def health_swap(dic,instructions, make_healthy):

    if make_healthy:

        unhealthy= ['bacon bits', 'melted chocolate','vegetable oil', 'potato', 'canola oil', 'peanut oil', 'coconut oil','corn oil', 'whole milk', 'coconut milk', 'soy milk', 'ice cream', 'sour cream','cream cheese',    'american cheese', 'cottage cheese', 'mozzarella cheese', 'ricotta cheese', 'cream',  'all-purpose flour', 'bologna', 'sausage','vegetable oil', 'torillas', 'tortilla', 'rice', 'sugar', 'penne', 'linguine',    'fettuccine',    'spaghetti',    'lasagna',    'pasta salad',    'pasta',    'white bread',    'pancakes',    'milk',    'taco shell',    'french fries',    'mashed potatoes',    'sweet potatoes' ,   'potatoes',    'potato chips',    'hash browns',    'baking soda',    'beef jerky',    'beef noodle soup',    'blue cheese',    'bullion',    'camembert cheese',    'canned anchovy',    'canned corn',    'canned tomatoes',    'capocollo',    'chicken noodle soup',  'chicken soup',    'cream of vegetable soup',    'feta cheese',    'fish sauce',    'gouda cheese',    'hot pepper sauce',    'instant soup',    'italian salami',    'ketchup',    'marinade',    'mayonnaise',    'mortadella',    'ground beef',    'olives',    'onion soup',    'oyster sauce',    'paremsan cheese',    'pepperoni',    'pickle',    'pickled eggplant',    'pickled peppers',    'prosciutto',    'queso seco',    'ranch dressing',    'relish',    'romano cheese',    'roquefort cheese',    'salad dressing',    'salami',    'salt and pepper',    'salt cod',    'salted butter',    'salted mackerel',    'lightly salted',    'salted',    'sauerkraut',    'sea salt',    'salt',    'smoked herring',    'smoked salmon',    'smoked white fish',    'soup cube',    'soup',    'soy sauce',    'steak sauce',    'stock cube',    'stock',    'table salt',    'teriyaki sauce',    'tomato soup',    'turkey bacon',    'turkey salami',    'vegetable soup',    'chocolate',    'beef',    'pork',    'breaded fish',    'fried fish',    'egg whites',    'egg white',    'whole eggs',    'eggs',    'egg',    'whole egg',    'chorizo sausage',    'croissants',    'brioches',    'butter',    'margarine',    'cheddar cheese',    'cheese',    'chilli powder']

        healthy_substitutes = { 'bacon bits':'crushed almonds', 'melted chocolate':'lemon juice',  'potato': 'zucchini',   'canola oil': 'olive oil',     'peanut oil': 'olive oil',     'corn oil': 'olive oil',     'sunflower oil': 'olive oil',     'sesame oil' : 'olive oil',     'coconut oil' : 'olive oil', 'all-purpose flour': 'whole wheat all-purpose flour'  ,   'whole milk': 'low-fat milk',     'coconut milk' : 'almond milk',     'soy milk' : 'almond milk',     'ice cream': 'low-fat frozen yoghurt',     'sour cream': 'plain low-fat yoghurt',    'cream cheese': 'fat-free cream cheese',     'american cheese': 'fat-free cheese',    'cottage cheese': 'low-fat cottage cheese',    'mozzarella cheese': 'part-skim milk mozzarella cheese',    'ricotta cheese': 'part-skim milk ricotta cheese',    'cream': 'low-fat milk',  'bologna': 'low-fat bologna',    'sausage': 'lean ham',    'vegetable oil': 'coconut oil',    'tortillas': 'lettuce leaves',    'tortilla': 'lettuce leaves',    'rice': 'cauliflower rice',    'sugar': 'imitation sugar',    'penne': 'whole wheat penne',    'linguine': 'whole wheat linguine',    'fettuccine': 'whole wheat fettuccine',    'spaghetti': 'spaghetti squash',    'lasagna': 'vegetable lasagna',    'pasta salad': 'mixed vegetables',    'pasta': 'veggie noodles',    'white bread': 'whole wheat bread',    'pancakes': 'whole wheat pancakes',    'milk': 'almond milk',    'taco shell': 'lettuce wrap',    'french fries': 'butternut squash fries',    'mashed potatoes': 'mashed cauliflower',    'sweet potatoes': 'zucchini',    'potatoes': 'zucchini',    'potato chips': 'kale chips',    'hash browns': 'squash',    'baking soda': 'sodium-free baking soda',    'beef noodle soup': 'mushroom broth',    'blue cheese': 'part-skim milk mozzarella cheese',    'bullion': 'mushroom broth',    'camembert cheese': 'part-skim milk mozzarella cheese',    'canned anchovy': 'low-sodium sardines',    'canned corn': 'fresh corn',    'canned tomatoes': 'fresh tomatoes',    'capocollo': 'low-sodium ham',    'chicken noodle soup': 'mushroom broth',    'chicken soup': 'mushroom broth',    'cream of vegetable soup': 'mushroom broth',      'feta cheese': 'part-skim milk mozzarella cheese',    'fish sauce': 'vinegar',    'gouda cheese': 'part-skim milk mozzarella cheese',    'hot pepper sauce': 'red pepper flakes',    'instant soup': 'mushroom broth',    'italian salami': 'low-sodium ham',    'ketchup': 'low-sodium ketchup',    'marinade': 'flavored vinegar',    'mayonnaise': 'yogurt',    'mortadella': 'low-sodium ham',    'ground beef': 'extra-lean ground beef',    'olives': 'baked grapes',    'onion soup': 'mushroom broth',    'oyster sauce': 'vinegar',    'paremsan cheese': 'part-skim milk mozzarella cheese',    'pepperoni': 'low-sodium ham',    'pickle': 'cucumber',    'pickled eggplant': 'eggplant',    'pickled peppers': 'fresh chiles',    'prosciutto': 'low-sodium ham',    'queso seco': 'part-skim milk mozzarella cheese',    'ranch dressing': 'balsamic vinegar',    'relish': 'low-sodium sweet relish',    'romano cheese': 'part-skim milk mozzarella cheese',    'roquefort cheese': 'part-skim milk mozzarella cheese',    'salad dressing': 'olive oil',    'salami': 'low-sodium ham',    'salt and pepper': 'pepper',    'salt cod': 'fresh cod',    'salted butter': 'unsalted butter',    'salted mackerel': 'fresh mackerel',    'lightly salted': '',    'salted': '',    'sauerkraut': 'chopped cabbage',    'sea salt': 'sesame oil',    'salt': 'low-sodium salt substitute',    'smoked herring': 'seared herring',    'smoked salmon': 'fresh salmon',    'smoked white fish': 'seared white fish',    'soup cube': 'mushroom broth',    'soup': 'vegetable puree',    'soy sauce': 'low-sodium soy sauce',    'steak sauce': 'low-sodium steak sauce',    'stock cube': 'mushroom broth',    'stock': 'mushroom broth',    'table salt': 'sesame oil',    'teriyaki sauce': 'vinegar',    'tomato soup': 'mushroom broth',    'turkey bacon': 'fresh turkey strips',    'turkey salami': 'low-sodium ham',    'vegetable soup': 'mushroom broth',    'chocolate': 'carob',    'beef': 'beef(trimmed of external fat)',    'pork': 'lean smoked ham',    'breaded fish': 'unbreaded shellfish',    'fried fish': 'unbreaded shellfish',    'egg whites':'egg whites',    'egg white':'egg white',    'whole eggs': 'egg whites',    'eggs': 'egg whites',    'egg': 'egg whites',    'whole egg': 'egg whites',    'chorizo sausage': 'turkey sausage',    'croissants': 'hard french rolls',    'brioches': 'hard french rolls',    'butter': 'whipped butter',    'margarine': 'diet margarine',    'cheddar cheese': 'fat-free cheese',    'cheese': 'low-fat cheese',    'chilli powder': 'green chilli powder'}

        substitutions = 0
        deleting_ing = []
        deleted_map = {}
        for ing in dic.keys():
            tokens = word_tokenize(ing)
            for token in tokens:
                if token in unhealthy:
                    deleting_ing.append(ing)
                    substitutions += 1

        for ing in deleting_ing:
            if ing in dic.keys():
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in healthy_substitutes.keys():
                        dic[healthy_substitutes[token]] = dic[ing]

                        deleted_map[ing] = healthy_substitutes[token]
                del dic[ing]

        for i,instruction in enumerate(instructions):
            for ing in deleting_ing:
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in instruction:
                        if token in healthy_substitutes.keys():
                            instructions[i] = instruction.replace(token,healthy_substitutes[token])
                        else:
                            for old_ing in deleted_map.keys():
                                if token in old_ing:
                                    instructions[i] = instruction.replace(token, deleted_map[old_ing])


        if substitutions == 0:
            dic['quinoa'] = '4 cups'
            instructions.append("Serve with quinoa.")

        return dic,instructions

    else:

        healthy = { 'quinoa', 'kale', 'olive oil',  'zucchini',   'low-fat milk',     'almond milk',   'low-fat frozen yoghurt', 'fat-free cream cheese',     'fat-free cheese',    'low-fat cottage cheese',  'part-skim milk mozzarella cheese',     'part-skim milk ricotta cheese',  'low-fat milk',    'almond flour',   'low-fat bologna',   'lean ham',   'coconut oil',    'lettuce leaves',    'lettuce leaf',    'cauliflower rice',    'imitation sugar',    'whole wheat penne',    'whole wheat linguine',    'whole wheat fettuccine',     'spaghetti squash',   'vegetable lasagna',    'mixed vegetables',   'veggie noodles',    'whole wheat bread',  'whole wheat pancakes',    'almond milk',     'lettuce wrap',   'butternut squash fries',     'mashed cauliflower',     'kale chips','kale',   'squash',    'sodium-free baking soda',     'mushroom broth',     'part-skim milk mozzarella cheese',   'low-sodium sardines',    'fresh corn',    'fresh tomatoes',   'low-sodium ham',    'low-sodium ketchup',     'cucumber',     'eggplant',    'fresh chiles',    'balsamic vinegar',  'low-sodium sweet relish',        'lightly salted' , 'vegetable puree',  'low-sodium soy sauce',   'low-sodium steak sauce', 'egg whites',    'egg white'   , 'turkey sausage',  'margarine',  'fat-free cheese',   'low-fat cheese'}

        unhealthy_substitutes = {'quinoa':'french fries', 'olive oil': 'canola oil',  'zucchini': 'potato',     'almond milk': 'whole milk',      'frozen yogurt': 'ice cream', 'fat-free cream cheese': 'cream cheese',      'low-fat cottage cheese': 'cottage cheese',  'part-skim milk mozzarella cheese': 'mozzarella cheese',     'part-skim milk ricotta cheese': 'ricotta cheese',  'low-fat milk': 'whole milk',    'almond flour': 'flour',   'low-fat bologna': 'bologna',   'lean ham': 'ham',   'coconut oil': 'canoloa oil',    'lettuce leaves': 'tortillas',    'lettuce leaf': 'tortilla',    'cauliflower rice': 'rice',    'imitation sugar': 'sugar',    'whole wheat penne': 'penne',    'whole wheat linguine': 'linguine',    'whole wheat fettuccine': 'fettuccine',     'spaghetti squash': 'spaghetti','kale':'potato chips' ,  'vegetable lasagna': 'lasagna',    'mixed vegetables': 'hash browns',   'veggie noodles': 'noodles',    'whole wheat bread': 'bread',  'whole wheat pancakes': 'pancakes',     'lettuce wrap': 'taco',   'butternut squash fries': 'french fries',     'mashed cauliflower': 'mashed potatoes',     'kale chips':'chips',    'squash':'potato',    'sodium-free baking soda': 'baking soda',     'mushroom broth': 'beef broth',   'low-sodium sardines': 'sardines',    'fresh corn': 'canned corn',    'fresh tomatoes': 'canned tomatoes',   'low-sodium ham': 'ham',    'low-sodium ketchup': 'ketchup',     'cucumber': 'pickle',     'eggplant': 'potato',    'fresh chiles':'fries',    'balsamic vinegar':'ranch',  'low-sodium sweet relish':'relish',        'lightly salted':'salted',    'vegetable puree': 'fries',  'low-sodium soy sauce': 'soy sauce',   'low-sodium steak sauce': 'steak sauce', 'egg whites': 'eggs',    'egg white': 'egg'   , 'turkey sausage': 'bacon',  'margarine': 'butter', 'fat-free cheese':'cheese',   'low-fat cheese':'cheese'}

        substitutions = 0
        deleting_ing = []
        deleted_map = {}
        for ing in dic.keys():
            tokens = word_tokenize(ing)
            for token in tokens:
                if token in healthy:
                    deleting_ing.append(ing)
                    substitutions += 1

        for ing in deleting_ing:
            if ing in dic.keys():
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in unhealthy_substitutes.keys():
                        dic[unhealthy_substitutes[token]] = dic[ing]

                        deleted_map[ing] = unhealthy_substitutes[token]
                del dic[ing]

        for i,instruction in enumerate(instructions):
            for ing in deleting_ing:
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in instruction:
                        if token in unhealthy_substitutes.keys():
                            instructions[i] = instruction.replace(token,unhealthy_substitutes[token])
                        else:
                            for old_ing in deleted_map.keys():
                                if token in old_ing:
                                    instructions[i] = instruction.replace(token, deleted_map[old_ing])

        if substitutions == 0:
            dic['melted chocolate'] = '1 cup'
            instructions.append("Coat in chocolate.")

        return dic,instructions

def asian_cuisine_swap(dic, instructions, make_asian):
    if make_asian:

        not_asian = { 'worcestershire sauce', 'apple cider vinegar', 'lettuce', 'celery', 'cabbage', 'red pepper flakes', 'pasta', 'spaghetti', 'parsley', 'basil', 'harissa', 'bbq sauce', 'barbecue sauce', 'milk' }

        asian_substitutes = { 'worcestershire sauce': 'hoisin sauce', 'apple cider vinegar': 'rice vinegar', 'lettuce': 'bok choy', 'celery': 'chinese celery', 'cabbage': 'kimchi', 'red pepper flakes': 'chili pepper flakes', 'milk': 'coconut milk', 'pasta': 'glass noodles', 'spaghetti': 'udon noodles', 'parsley': 'green onion', 'basil': 'sesame seeds', 'harissa': 'gochujang', 'bbq sauce': 'teriyaki sauce', 'barbecue sauce': 'teriyaki sauce' }

        substitutions = 0
        deleting_ing = []
        deleted_map = {}
        for ing in dic.keys():
            tokens = word_tokenize(ing)
            for token in tokens:
                if token in not_asian:
                    deleting_ing.append(ing)
                    substitutions += 1

        for ing in deleting_ing:
            if ing in dic.keys():
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in asian_substitutes.keys():
                        dic[asian_substitutes[token]] = dic[ing]

                        deleted_map[ing] = asian_substitutes[token]
                del dic[ing]

        for i,instruction in enumerate(instructions):
            for ing in deleting_ing:
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in instruction:
                        if token in asian_substitutes.keys():
                            instructions[i] = instruction.replace(token,asian_substitutes[token])
                        else:
                            for old_ing in deleted_map.keys():
                                if token in old_ing:
                                    instructions[i] = instruction.replace(token, deleted_map[old_ing])

        if substitutions == 0:
            dic['white rice'] = '3 cups'
            dic['soy sauce'] = '2 tablespoons'
            dic['sesame seeds'] = '1 teaspoon'
            instructions.append("Sprinkle sesame seeds on top of your dish. Serve with a side of rice and soy sauce.")

        return dic,instructions

    else:

        asian = { 'hoisin sauce', 'rice vinegar', 'bok choy', 'chinese celery', 'kimchi', 'chili pepper flakes', 'glass noodles', 'udon noodles', 'green onion', 'sesame seeds', 'gochujang', 'teriyaki sauce', 'coconut milk' }

        not_asian_substitutes = { 'hoisin sauce': 'worcestershire sauce', 'rice vinegar': 'apple cider vinegar', 'bok choy': 'lettuce', 'chinese celery': 'celery', 'kimchi': 'cabbage', 'chili pepper flakes': 'red pepper flakes', 'coconut milk': 'milk', 'glass noodles': 'pasta', 'udon noodles': 'spaghetti', 'green onion': 'parsley', 'sesame seeds': 'basil', 'gochujang': 'harissa', 'teriyaki sauce': 'barbecue sauce' }

        substitutions = 0
        deleting_ing = []
        deleted_map = {}
        for ing in dic.keys():
            tokens = word_tokenize(ing)
            for token in tokens:
                if token in asian:
                    deleting_ing.append(ing)
                    substitutions += 1

        for ing in deleting_ing:
            if ing in dic.keys():
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in not_asian_substitutes.keys():
                        dic[not_asian_substitutes[token]] = dic[ing]

                        deleted_map[ing] = not_asian_substitutes[token]
                del dic[ing]

        for i,instruction in enumerate(instructions):
            for ing in deleting_ing:
                tokens = word_tokenize(ing)
                for token in tokens:
                    if token in instruction:
                        if token in not_asian_substitutes.keys():
                            instructions[i] = instruction.replace(token,not_asian_substitutes[token])
                        else:
                            for old_ing in deleted_map.keys():
                                if token in old_ing:
                                    instructions[i] = instruction.replace(token, deleted_map[old_ing])

        return dic,instructions

nlp = spacy.load('en_core_web_lg')

if __name__ == '__main__':
    read_in_url()
