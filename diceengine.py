#!/usr/bin/env python3

"""The actual background processing of data"""


from copy import deepcopy


class ResultList(object):
    """Holds a dictionary of results for a comparison

    e.g. {10: 0.7, 11: 0.8}"""
   
    def __init__(self, result_list=None):
        # Using sentinel value to avoid mutable default
        self.result_list = result_list if result_list else {}

    def __repr__(self):
        return str(self.result_list)

    def __getitem__(self, key):
        return self.result_list[key]

    def __setitem__(self, key, value):
        self.result_list[key] = value

    def items(self):
        return self.result_list.items()

class Distrib(object):
    """Holds a distribution. Is 0 initialized!!!

    example: {1: 0.5, 2: 0.5} for a d2
    """

    def __init__(self, distrib=None):
        # Using sentinel value to avoid mutable default
        self.distrib = distrib if distrib else {}

    def __repr__(self):
        return str(self.distrib)

    def __getitem__(self, key):
        # returning 0 if no key is found makes adding easy
        if key in self.distrib:
            return self.distrib[key]
        else:
            return 0

    def __setitem__(self, key, value):
        self.distrib[key] = value

    def items(self):
        return self.distrib.items()


# There is also the normal python int
# And the normal python list

class Diceengine(object):
    """Wrapper for static objects that manipulate probabilites"""

    @staticmethod
    def exception(message):
        raise Exception("Diceengine exception: {}".format(message))

    @staticmethod
    def res(result, distrib):
        # convert integer to 100% change distribution
        if type(distrib) == int:
            distrib = Distrib({distrib: 1})
        if not isinstance(result, ResultList) or not isinstance(distrib, Distrib):
            Diceengine.exception("Can't resolve {} with {}".format(type(result), type(distrib)))

        # sum distribution
        average_value = 0
        for dice, prop in distrib.items():
            average_value += dice * prop

        resolved_result = ResultList()
        # multiply every change for every value (ac) with average damage
        for value, prop in result.items():
            resolved_result[value] = prop * average_value
        return resolved_result

    @staticmethod
    def reselse(result, distrib_if, distrib_else):
        # NOTE: Copied from res
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
        average_value_if = 0
        for dice, prop in distrib_if.items():
            average_value_if += dice * prop

        average_value_else = 0
        for dice, prop in distrib_else.items():
            average_value_else += dice * prop

        resolved_result = ResultList()
        # multiply every change for every value (ac) with average damage
        for value, prop in result.items():
            resolved_result[value] = prop * average_value_if + (1 - prop) * average_value_else
        return resolved_result


    @staticmethod
    def roll(dicenum, dicesides):
        """Generate probability distribution for the roll of dicenum dice with dicesides sides"""
        # TODO: do proper maths! This is easy stuff!
        results = Distrib({0: 1})
        # add dicenum dice
        for _ in range(dicenum):
            # Dictionary to store next probability distribution
            results_new = Distrib()
            # add every possible dice throw to every existing result
            for i in range(1, dicesides + 1):
                for value, prop in results.items():
                    results_new[value + i] += prop / dicesides
            results = deepcopy(results_new)
        return results

    @staticmethod
    def add(left, right):
        """Can add two diceprops or one diceprop and one integer or two integers"""
        # Note that adding is cumutative so it only has to be implemented one way

        if type(left) == int:
            if type(right) == int:
                # add int to int
                return left + right
            elif type(right) == list:
                # add int to list
                return [x + left for x in right]
            elif isinstance(right, Distrib):
                # add int to distrib
                new_distrib = Distrib()
                # add left to every key in Distrib
                for dice, prop in right.items():
                    new_distrib[dice + left] = prop
                return new_distrib
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

        Diceengine.exception("Can't add {} to {}".format(type(left), type(right)))

    @staticmethod
    def sub(left, right):
        """Subtracts two Distribs or a Distrib and an integer"""
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
        """Multiplies Ints, Distribs and Lists"""
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
        elif type(left) == list:
            if type(right) == int:
                # already implemented before
                return Diceengine.mul(right, left)
        elif isinstance(left, Distrib):
            if type(right) == int:
                # already implemented
                return Diceengine.mul(right, left)

        Diceengine.exception("Can't multiply {} with {}".format(type(left), type(right)))

    @staticmethod
    def div(left, right):
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
    def compare(distrib, list_input, operator):
        """Compares distribution to listinput according to operator (distribution is left)"""
        if type(list_input) != list or not isinstance(distrib, Distrib):
            Diceengine.exception("Can't compare {} with {}".format(type(list_input), type(distrib)))
        if operator not in ['<=', '>=', '<', '>', '==']:
            Diceengine.exception("Unknown operator {}".format(operator))

        resultlist = ResultList()

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
        # convert integers to list
        if type(left) == int:
            left = [left]
        if type(right) == int:
            right = [right]
        if type(right) == list and isinstance(left, Distrib):
            return Diceengine.compare(left, right, '>=')
        elif type(left) == list and isinstance(right, Distrib):
            # switched operand switch comparison
            return Diceengine.compare(right, left, '<=')
        Diceengine.exception("Can't compare {} with {}".format(type(left), type(right)))

    @staticmethod
    def greater(left, right):
        # NOTE: Copied from greaterorequal
        # convert integers to list
        if type(left) == int:
            left = [left]
        if type(right) == int:
            right = [right]
        if type(right) == list and isinstance(left, Distrib):
            return Diceengine.compare(left, right, '>')
        elif type(left) == list and isinstance(right, Distrib):
            # switched operand switch comparison
            return Diceengine.compare(right, left, '<')
        Diceengine.exception("Can't compare {} with {}".format(type(left), type(right)))

    @staticmethod
    def equal(left, right):
        # NOTE: Copied from greaterorequal
        # convert integers to list
        if type(left) == int:
            left = [left]
        if type(right) == int:
            right = [right]
        if type(right) == list and isinstance(left, Distrib):
            return Diceengine.compare(left, right, '==')
        elif type(left) == list and isinstance(right, Distrib):
            # switched operand switch comparison
            return Diceengine.compare(right, left, '==')
        Diceengine.exception("Can't compare {} with {}".format(type(left), type(right)))

    @staticmethod
    def lessorequal(left, right):
        return Diceengine.greaterorequal(right, left)

    @staticmethod
    def less(left, right):
        return Diceengine.greater(right, left)

if __name__ == "__main__":
    d1 = Diceengine.rollprop(1, 20)
    d2 = Diceengine.rollprop(1, 3)
    l = [1, 2, 3]

    print(Diceengine.greater(d1, 11))
