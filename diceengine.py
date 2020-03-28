#!/usr/bin/env python3

"""Does aritmetic on stochastical distributions.

Datatypes:
Result List: Holds results and average values
Distrib: Holds values and probabilities
list: (Python) holds values
int: (Pythoon) holds one value
"""

# note that comb only exists in python 3.8
from math import factorial, floor, comb, inf


class ResultList(object):
    """Holds a dictionary with values and results

    e.g. {10: 0.7, 11: 0.8}"""
   
    def __init__(self, result_list=None):
        # Using sentinel value to avoid mutable default
        self.result_list = result_list if result_list else {}

    def __repr__(self):
        return str(self.result_list)

    def __getitem__(self, key):
        """Return value of key if existing else 0"""
        return self.result_list[key] if key in self.result_list else 0

    def __setitem__(self, key, value):
        self.result_list[key] = value

    def items(self):
        """Return iterable of internal result list"""
        return self.result_list.items()


class Distrib(object):
    """Holds a stocahstic distribution of values and probabilites

    example: {1: 0.5, 2: 0.5} for a d2
    """

    def __init__(self, distrib=None):
        # Using sentinel value to avoid mutable default
        self.distrib = distrib if distrib else {}

    def __repr__(self):
        return str(self.distrib)

    def __getitem__(self, key):
        """Returns probability of key if key exists else 0"""
        return self.distrib[key] if key in self.distrib else 0

    def __setitem__(self, key, value):
        self.distrib[key] = value

    def items(self):
        """Return iterable of distribution"""
        return self.distrib.items()

    def average(self):
        """Returns average value of statistic distribution"""
        # multiply every entry with changse to occur
        return sum([dice * prop for dice, prop in self.items()])

class Diceengine(object):
    """Arithmetic methods for handling distributions"""
    # NOTE: leave in class wrapper as to not seem to similar to default methods

    @staticmethod
    def exception(message):
        """Raises an exception of the Diceengine"""
        # TODO: more nuonced custom exceptions
        raise Exception("Diceengine exception: {}".format(message))

    @staticmethod
    def choose(left, right):
        """Indexes Distrib (left) with list (right)"""
        if not isinstance(left, Distrib) or not type(right) == list:
            Diceengine.exception("Can't choose {} from {}".format(type(left), type(right)))
        ret_distrib = Distrib()
        for dice, prop in left.items():
            if dice in right:
                ret_distrib[dice] = prop
        return ret_distrib

    @staticmethod
    def res(result, distrib):
        """Evaluates average damage (distrib) over result

        This is used to convert a hitchangse over ac table to a damage over ac table"""
        if type(distrib) == int:
            distrib = Distrib({distrib: 1})
        if not isinstance(result, ResultList) or not isinstance(distrib, Distrib):
            Diceengine.exception("Can't resolve {} with {}".format(type(result), type(distrib)))

        # cache average
        distrib_average = distrib.average()

        # place to store result
        resolved_result = ResultList()

        # to resolve check hitchangse (stored for every ac(key) as value)
        # and multiply with distrib_average
        for value, prop in result.items():
            resolved_result[value] = prop * distrib_average
        return resolved_result

    @staticmethod
    def resunary(value):
        """Return resolution of a single entry.

        Implemented for Distribution only as average.
        For int just return value of int"""
        # NOTE: value is wrapped in a ResultList because it fundamentaly is a result
        # and this language has no float type
        if type(value) == int:
            return ResultList({"Int": value})

        if not isinstance(value, Distrib):
            Diceengine.exception("Can't resolve {}".format(type(value)))

        return ResultList({"AV": value.average()})

    @staticmethod
    def reselse(result, distrib_if, distrib_else):
        """Evaluates average damage of two distributions over one result (damage on hit and miss)
        This is used to convert a hitchangse over ac table to damage over ac table.

        result: hitchangse
        distrib_if: when hit then do this damage.
        distrib_else: when miss then do this damage
        """

        # convert integer to 100% change distribution
        if type(distrib_if) == int:
            distrib_if = Distrib({distrib_if: 1})
        if type(distrib_else) == int:
            distrib_else = Distrib({distrib_else: 1})

        if not isinstance(result, ResultList) \
           or not isinstance(distrib_if, Distrib) \
           or not isinstance(distrib_else, Distrib):
            Diceengine.exception("Can't resolve {} with {} and {}".format(type(result),
                                                                          type(distrib_if),
                                                                          type(distrib_else)))

        # sum distribution
        average_value_if = distrib_if.average()
        average_value_else = distrib_else.average()

        # to store result
        resolved_result = ResultList()

        # to resolve check hitchangse (stored for every ac(key) as value)
        # and multiply with distrib_average on hit else with miss
        for value, prop in result.items():
            resolved_result[value] = prop * average_value_if + (1 - prop) * average_value_else
        return resolved_result

    @staticmethod
    def reselsediv(result, distrib):
        """Evaluates average damage over dc uses distrib if successful else divides (integer) by 2 if unsuccessful"""
        return Diceengine.reselse(result, Diceengine.div(distrib, 2))

    @staticmethod
    def roll(n, s):
        """Generate probability distribution for the roll of n dice with s sides"""
        # NOTE: fallback for python < 3.8
        # def nck(n, k):
        #     return factorial(n) / (factorial(k)) / factorial(n - k)
        results = Distrib()
        for p in range(1, s * n + 1):
            c = (p - n) // s
            P = sum([(-1) ** k * comb(n, k) * comb(p - s * k - 1, n - 1) for k in range(0, c + 1) ]) / s ** n
            if P != 0:
                results[p] = P
        return results

    @staticmethod
    def rollsingle(dice):
        """Generates distribution for one single diceroll"""
        if type(dice) != int:
            Diceengine.exception("Can't roll with {}".format(type(dice)))
        return Distrib({n: 1 / dice for n in range(1, dice + 1)})

    @staticmethod
    def rolladvantage(dice):
        """Generates distribution for one roll with advantage
        (Roll twice and pick the highest)"""
        # returns probability to roll x with advantage
        advroll = lambda x: 2 / dice ** 2 * (x - 1) + (1 / dice) ** 2
        if type(dice) != int:
            Diceengine.exception("Can't roll with {}".format(type(dice)))
        return Distrib({n: advroll(n) for n in range(1, dice + 1)})

    @staticmethod
    def rolldisadvantage(dice):
        """Generates distribution for one roll with disadvantage
        (Roll twice and pick the lowest)"""
        # returns probability to roll x with disadvantage
        disadvroll = lambda x: 2 / dice ** 2 * (dice - x) + (1 / dice) ** 2
        if type(dice) != int:
            Diceengine.exception("Can't roll with {}".format(type(dice)))
        return Distrib({n: disadvroll(n) for n in range(1, dice + 1)})

    @staticmethod
    def rollhigh(n, s, nh):
        """Roll n s sided dice and pick the highest nh"""

        if type(n) != int or type(s) != int or type(nh) != int:
            Diceengine.exception("Can't rollhigh with {}, {} and {}".format(type(n), type(s), type(nh)))

        # TODO HACK proper maths
        #
        # This basically summs up all paths that lead to a certain outcome by traversing all of them.
        # Number of calls to count_children is s ** n + 1 or something so yeah ... quite big

        # traverses every dice roll combination
        def count_children(s, n_left, results, distrib):
            """Traverses every dice roll combination by recursion
            s: dicesides
            n_left: rolls left
            results: currently picked results(max rolls)
            distrib: place to hold results"""

            if n_left == 0:
                # last node. Count one more path to the result
                distrib[sum(results)] += 1
                return
            # traverse the tree
            for i in range(1, s + 1):
                results_min = min(results)
                new_results = results.copy()
                if i > results_min:
                    new_results[results.index(results_min)] = i
                count_children(s, n_left - 1, new_results, distrib)

        # use distrib to store combinations because after dividing by total number of
        # possible combinations it becomes a probability and because it is 0 initialized
        combinations = Distrib()

        # count possible results for every outcome
        count_children(s, n, [0] * nh, combinations)

        # total number of combinations
        total = s ** n
        for key, value in combinations.items():
            combinations[key] = value / total
        return Distrib(combinations)

    @staticmethod
    def rolllow(n, s, nl):
        # NOTE: copied from rollhigh
        """Roll n s sided dice and take nl of the lowest rolls

        n = dicenum
        s = dicesides
        nh = number of heighest rolls picked
        """

        # TODO HACK proper maths
        #
        # This basically summs up all paths that lead to a certain outcome by traversing all of them.
        # Number of calls to count_children is s ** n + 1 or something so yeah ... quite big

        if type(n) != int or type(s) != int or type(nl) != int:
            Diceengine.exception("Can't rolllow with {}, {} and {}".format(type(n), type(s), type(nl)))

        # traverses every dice roll combination
        def count_children(s, n_left, results, distrib):
            """Traverses every dice roll combination by recursion
            s: dicesides
            n_left: rolls left
            results: currently picked results(max rolls)
            distrib: place to hold results"""
            if n_left == 0:
                distrib[sum(results)] += 1
                return
            # traverse the tree
            for i in range(1, s + 1):
                results_max = max(results)
                new_results = results.copy()
                if i < results_max:
                    new_results[results.index(results_max)] = i
                count_children(s, n_left - 1, new_results, distrib)

        # use distrib to store combinations because after dividing by total number of
        # possible combinations it becomes a probability and because it is 0 initialized
        combinations = Distrib()

        # count possible results for every outcome
        count_children(s, n, [inf] * nl, combinations)

        # total number of combinations
        total = s ** n
        for key, value in combinations.items():
            combinations[key] = value / total
        return Distrib(combinations)

    @staticmethod
    def add(left, right):
        """Add two variables together.

        add is cumtative

        int + int = int               (adds two ints)
        int + list = list             (adds int to every entry)
        int + distrib = distrib       (adds int to every key)
        distrib + disrib = distrib    (generates probabilities for all combinations of adding values)
        result + result = result      (combines list adding values where keys match)
        """
        # Note that adding is cumutative so it only has to be implemented one way
        if type(left) == int:
            if type(right) == int:
                return left + right
            elif type(right) == list:
                return [x + left for x in right]
            elif isinstance(right, Distrib):
                # new distrib to store results because keys change
                new_distrib = Distrib()
                for dice, prop in right.items():
                    new_distrib[dice + left] = prop
                return new_distrib
            # NOTE: copied from Diceengine.mul
            elif isinstance(right, ResultList):
                new_results = ResultList()
                for key, value in right.items():
                    new_results[key] = value + left
                return new_results

        elif type(left) == list:
            if type(right) == int:
                # has already been implemented
                return Diceengine.add(right, left)
        elif isinstance(left, Distrib):
            if type(right) == int:
                # has already been implemented
                return Diceengine.add(right, left)
            elif isinstance(right, Distrib):
                # add Distrib to Distrib
                new_distrib = Distrib()
                # adding two distributions together (e.g. 1d20 + 1d4) generates all possible
                # combinations and summes their changses over a given value
                for d1, p1 in left.items():
                    for d2, p2 in right.items():
                        new_distrib[d1 + d2] += p1 * p2
                return new_distrib
        elif isinstance(left, ResultList):
            if type(right) == int:
                # already implemented
                return Diceengine.add(right, left)
            elif isinstance(right, ResultList):
                ret_list = ResultList()
                # add Resultlist to resultlist
                for result, value in left.items():
                    ret_list[result] += value
                for result, value in right.items():
                    ret_list[result] += value
                return ret_list

        Diceengine.exception("Can't add {} to {}".format(type(left), type(right)))

    @staticmethod
    def sub(left, right):
        """ Subtracts one variable from another

        int - int = int               (subtracts two ints)
        list - int = list             (subtracts int from every entry)
        int - list = list             (subtracts every list entry from int to generate new list)
        int - distrib = distrib       (subtracts every distrib key form int to generate new distrib)
        distrib - int = distrib       (subtracts int from every key)
        distrib - disrib = distrib    (generates probabilities for all combinations of subtracting values)
        """
        # This basically just calls the add method
      
        # NOTE: copied from add
        if type(left) == int:
            if type(right) == int:
                # sub int from int
                return left - right
            elif type(right) == list:
                # sub list from int
                return [left - x for x in right]
            elif isinstance(right, Distrib):
                # sub distrib from int
                new_distrib = Distrib()
                # sub every key in distrib from left
                for dice, prop in right.items():
                    new_distrib[left - dice] = prop
                return new_distrib
        elif type(left) == list:
            if type(right) == int:
                # NOTE: copyied from above
                # sub int from list
                return [x - right for x in left]
        elif isinstance(left, Distrib):
            if type(right) == int:
                # NOTE: copied form above
                # sub int from Distrib
                new_distrib = Distrib()
                # sub int from every key in Distrib
                for dice, prop in left.items():
                    new_distrib[dice - right] = prop
                return new_distrib
            elif isinstance(right, Distrib):
                # sub Distrib from Distrib
                new_distrib = Distrib()
                # subbing two distributions from another (e.g. 1d20 + 1d4) generates all possible
                # combinations and summes their(outcomes) changses over a given value
                for d1, p1 in left.items():
                    for d2, p2 in right.items():
                        new_distrib[d1 - d2] += p1 * p2
                return new_distrib

        Diceengine.exception("Can't sub {} from {}".format(type(left), type(right)))

    @staticmethod
    def mul(left, right):
        """Multiplies two variables

        is cumutative
       
        int * int = int
        int * list = list
        int * distrib = distrib
        """
        if type(left) == int:
            if type(right) == int:
                return left * right
            elif type(right) == list:
                return [x * left for x in right]
            elif isinstance(right, Distrib):
                # NOTE: copied from sub
                new_distrib = Distrib()
                # mul every key in distrib with left
                for dice, prop in right.items():
                    new_distrib[left * dice] = prop
                return new_distrib
            elif isinstance(right, ResultList):
                new_results = ResultList()
                for key, value in right.items():
                    new_results[key] = value * left
                return new_results
        elif type(left) == list:
            if type(right) == int:
                # already implemented before
                return Diceengine.mul(right, left)
        elif isinstance(left, Distrib):
            if type(right) == int:
                # already implemented
                return Diceengine.mul(right, left)
        elif isinstance(left, ResultList):
            if type(right) == int:
                # already implemented
                return Diceengine.mul(right, left)

        Diceengine.exception("Can't multiply {} with {}".format(type(left), type(right)))

    @staticmethod
    def div(left, right):
        """Divides two variables with INTEGER DIVISION

        int / int = int
        list / int = list
        distrib / int = distrib"""
        if type(left) == int:
            if type(right) == int:
                # NOTE: Integer division!
                return left // right
        elif type(left) == list:
            if type(right) == int:
                # integer division for every element. Remove extra elements
                return list(set([x // right for x in left]))
        elif isinstance(left, Distrib):
            if type(right) == int:
                # integer divide every key
                # NOTE: careful this can generate multiple new entries
                new_distrib = Distrib()
                for dice, prop in left.items():
                    new_distrib[dice // 2] += prop
                return new_distrib

        Diceengine.exception("Can't divide {} by {}".format(type(left), type(right)))

    @staticmethod
    def compare(left, right, operator):
        """Calculates changse for distrib to result true if compared with operator for every list entry
        and returns ResultList with list_input as keys and probability for success as value"""

        if operator not in ['<=', '>=', '<', '>', '==']:
            Diceengine.exception("Unknown operator {}".format(operator))

        # Only compare against lists
        if type(left) == int:
            left = [left]
        if type(right) == int:
            right = [right]

        # assume to be comparing distrib to list input
        distrib = left
        list_input = right


        # switch direction for rest of the code
        # (so we only have to handle the case where left is the distribution)
        if type(distrib) == list and isinstance(list_input, Distrib):
            if op == '<=':
                op = '>='
            if op == ">=":
                op = "<="
            if op == "<":
                op = ">"
            if op == ">":
                op = "<"

        if type(list_input) != list or not isinstance(distrib, Distrib):
            Diceengine.exception("Can't compare {} with {}".format(type(list_input), type(distrib)))

        resultlist = ResultList()

        # summes win changse for every list entry and adds to result_list
        # TODO: could be done with list comprehension not sure if it's cleaner
        for comp in list_input:
            win_changse = 0
            for dice, prop in distrib.items():
                # compare to operator. distrib (dice) is left and list(comp) is right
                # sum winchangses
                if operator == '<=' and dice <= comp:
                    win_changse += prop
                elif operator == '>=' and dice >= comp:
                    win_changse += prop
                elif operator == '<' and dice < comp:
                    win_changse += prop
                elif operator == '>' and dice > comp:
                    win_changse += prop
                elif operator == '==' and dice == comp:
                    win_changse += prop
            resultlist[comp] = win_changse
        return resultlist

    @staticmethod
    def greaterorequal(left, right):
        """Calculates changse for distrib to be greater or equal then for every list entry
        and returns ResultList with list_input as keys and probability for success as value"""
        return Diceengine.compare(left, right, '>=')

    @staticmethod
    def greater(left, right):
        """Calculates changse for distrib to be greater then every list entry
        and returns ResultList with list_input as keys and probability for success as value"""
        return Diceengine.compare(left, right, '>')

    @staticmethod
    def equal(left, right):
        """Calculates changse for distrib to be equal to every list entry
        and returns ResultList with list_input as keys and probability for success as value"""
        return Diceengine.compare(left, right, '==')

    @staticmethod
    def lessorequal(left, right):
        """Calculates changse for distrib to be less or equal to every list entry
        and returns ResultList with list_input as keys and probability for success as value"""
        return Diceengine.compare(left, right, "<=")

    @staticmethod
    def less(left, right):
        """Calculates changse for distrib to be less then every list entry
        and returns ResultList with list_input as keys and probability for success as value"""
        return Diceengine.compare(left, right, "<")

if __name__ == "__main__":
    pass
