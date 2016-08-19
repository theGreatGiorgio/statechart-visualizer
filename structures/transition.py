import math
import structures.box

from structures.box import space
from structures.segment import Segment, get_box_segments, intersect
from typing import Tuple, Dict


class Transition:
    def __init__(self, source, target, guard: str = '', event: str = '', action: str = ''):
        self.source = source
        self.target = target
        self.guard = guard
        self.event = event
        self.action = action
        self._x1, self._x2, self._y1, self._y2 = 0, 0, 0, 0
        self.polyline = []

    @property
    def coordinates(self):
        """
        :return: the coordinates of insert and end points
        """
        if self.polyline:
            return self.polyline[0], self.polyline[-1]
        else:
            return (self._x1, self._y1), (self._x2, self._y2)

    @property
    def is_downward_transition(self):
        """
        :return: True if the transition is downward, False otherwise
        """
        return self.source in self.target.ancestors

    @property
    def segments(self):
        """
        :return: The list of segments that compose the Transition
        """

        def build(segments_list, i):
            if i >= len(self.polyline) - 1:
                return segments_list
            else:
                return build(segments_list + [Segment(self.polyline[i], self.polyline[i + 1])], i + 1)

        if self.polyline:
            return build([], 0)
        else:
            return [Segment((self._x1, self._y1), (self._x2, self._y2))]

    def update_coordinates(self, start: Tuple[float, float], end: Tuple[float, float]):
        """
        Set the coordinates values
        :param start: the transition starts at this point
        :param end: the transition ends at this point
        """
        (x1, y1), (x2, y2) = start, end
        self._x1, self._x2, self._y1, self._y2 = x1, x2, y1, y2

    def conflicts_with_boxes(self, coordinates: Dict):
        """
        Compute the intersections with the boxes in parameter and this transition.
        Note that only the boxes intersected unrelated the source and the target will
        be added to the list returned.
        :param coordinates: the dict linking the boxes with their coordinates
        :return: the list of boxes intersected
        """

        def conflict(box):
            for segment1 in self.segments:
                for segment2 in get_box_segments(box, coordinates):
                    if intersect(segment1, segment2):
                        return True
            return False

        conflict_list = []
        for box in coordinates.keys():
            if box not in self.target.ancestors and box != self.source and box != self.target:
                if conflict(box):
                    conflict_list.append(box)
        return conflict_list

    def conflicts_with_transitions(self, transitions):
        """
        Compute the conflicts with the other transitions in parameter.
        :param transitions: the list of transitions to compute the intersection
        :return: the list of transitions intersected
        """

        def conflict(transition):
            for segment1 in self.segments:
                for segment2 in transition.segments:
                    if intersect(segment1, segment2):
                        return True
            return False

        conflict_list = []
        for transition in transitions:
            if self != transition:
                if conflict(transition):
                    conflict_list.append(transition)
        return conflict_list

    def __str__(self):
        return "Transition : " + self.source.name + " -> " + self.target.name

    def __repr__(self):
        return self.__str__()


def zone_of(box1, box2, coordinates):
    """
    box2 is ___ of box1
    /!\ deprecated : use a RootBox with root_box.zone(box1, box2) instead

    :param box1: the box reference
    :param box2: the box to determine the zone
    :param coordinates: the coordinates dictionary Dict[Box: (int, int)]
    :return: the area of box number 2 relative to the box number 1
    """
    x1, y1, x2, y2 = coordinates[box1]
    x3, y3, x4, y4 = coordinates[box2]
    x1, y1 = ((x1 + x2) / 2, (y1 + y2) / 2)
    x2, y2 = ((x3 + x4) / 2, (y3 + y4) / 2)
    if x1 <= x2 and y1 >= y2:
        return 'northeast'
    elif x1 >= x2 and y1 >= y2:
        return 'northwest'
    elif x1 >= x2 and y1 <= y2:
        return 'southwest'
    else:
        return 'southeast'


def acceptance_zone(box1, box2, axis, coordinates):
    """
    Check and compute if it is possible to draw a transition directly to another box
    with just one line
    """
    box1_coordinates = coordinates[box1]
    box2_coordinates = coordinates[box2]
    if axis == 'horizontal':
        x1, x2 = box1_coordinates[1], box1_coordinates[3]
        x3, x4 = box2_coordinates[1], box2_coordinates[3]
    else:
        x1, x2 = box1_coordinates[0], box1_coordinates[2]
        x3, x4 = box2_coordinates[0], box2_coordinates[2]
    if x1 < x2 and x3 < x4:
        x = [x1, x2, x3, x4]
        x.remove(min(x))
        x.remove(max(x))
        a, b = min(x), max(x)
        if (a >= x1 and b <= x2) and (a >= x3 and b <= x4):
            return a, b


def classic_arrow(transition, coordinates):
    """
    gives the polyline list for a classic transition arrow

    :param transition: the transition to determines the polyline
    :param coordinates: the coordinates of the boxes ; Dict[Box: (int, int)]
    :return: a list containing the points of the polyline
    """
    source = transition.source
    target = transition.target
    x1, y1, x2, y2 = coordinates[source]
    x3, y3, x4, y4 = coordinates[target]

    generate_list = lambda zone: list(
        filter(lambda t: zone_of(source, t.target, coordinates) == zone, source.transitions))

    if source.parent.axis == 'horizontal' and zone_of(source, target, coordinates) == 'northwest':
        l = generate_list('northwest')
        l.sort(key=lambda t: math.sqrt((x1 - coordinates[t.target][2]) ** 2 +
                                       (y1 - (
                                           coordinates[t.target][3] +
                                           coordinates[t.target][1]) / 2) ** 2))
        target_counter = len(l)
        target_index = l.index(transition)
        w = x2 - x1
        x = x1 + w / (target_counter + 1) + target_index * w / (target_counter + 1)
        y = (y3 + y4) / 2
        return [(x, y1), (x, y), (x4, y)]
    elif source.parent.axis == 'horizontal' and zone_of(source, target, coordinates) == 'northeast':
        l = generate_list('northeast')
        l.sort(key=lambda t: math.sqrt((x2 - coordinates[t.target][0]) ** 2 +
                                       (y1 - (
                                           coordinates[t.target][3] +
                                           coordinates[t.target][1]) / 2) ** 2))
        target_counter = len(l)
        target_index = l.index(transition)
        w = x2 - x1
        x = x2 - w / (target_counter + 1) - target_index * w / (target_counter + 1)
        y = (y3 + y4) / 2
        return [(x, y1), (x, y), (x3, y)]
    elif source.parent.axis == 'horizontal' and zone_of(source, target, coordinates) == 'southwest':
        l = generate_list('southwest')
        l.sort(key=lambda t: math.sqrt((x1 - coordinates[t.target][2]) ** 2 +
                                       (y2 - (
                                           coordinates[t.target][3] +
                                           coordinates[t.target][1]) / 2) ** 2))
        target_counter = len(l)
        target_index = l.index(transition)
        w = x2 - x1
        x = x1 + w / (target_counter + 1) + target_index * w / (target_counter + 1)
        y = (y3 + y4) / 2
        return [(x, y2), (x, y), (x4, y)]
    elif source.parent.axis == 'horizontal' and zone_of(source, target, coordinates) == 'southeast':
        l = generate_list('southeast')
        l.sort(key=lambda t: math.sqrt((x2 - coordinates[t.target][0]) ** 2 +
                                       (y2 - (
                                           coordinates[t.target][3] +
                                           coordinates[t.target][1]) / 2) ** 2))
        target_counter = len(l)
        target_index = l.index(transition)
        w = x2 - x1
        x = x2 - w / (target_counter + 1) - target_index * w / (target_counter + 1)
        y = (y3 + y4) / 2
        return [(x, y2), (x, y), (x3, y)]
    elif source.parent.axis == 'vertical' and zone_of(source, target, coordinates) == 'northwest':
        l = generate_list('northwest')
        l.sort(
            key=lambda t: math.sqrt((x1 - (
                coordinates[t.target][0] + coordinates[t.target][2]) / 2) ** 2 +
                                    (y1 - coordinates[t.target][3]) ** 2))
        target_counter = len(l)
        target_index = l.index(transition)
        h = y2 - y1
        x = (x3 + x4) / 2
        y = y1 + h / (target_counter + 1) + target_index * h / (target_counter + 1)
        return [(x1, y), (x, y), (x, y4)]
    elif source.parent.axis == 'vertical' and zone_of(source, target, coordinates) == 'northeast':
        l = generate_list('northeast')
        l.sort(
            key=lambda t: math.sqrt((x2 - (
                coordinates[t.target][0] + coordinates[t.target][2]) / 2) ** 2 +
                                    (y1 - coordinates[t.target][3]) ** 2))
        target_counter = len(l)
        target_index = l.index(transition)
        h = y2 - y1
        x = (x3 + x4) / 2
        y = y1 + h / (target_counter + 1) + target_index * h / (target_counter + 1)
        return [(x2, y), (x, y), (x, y4)]
    elif source.parent.axis == 'vertical' and zone_of(source, target, coordinates) == 'southwest':
        l = generate_list('southwest')
        l.sort(
            key=lambda t: math.sqrt((x1 - (
                coordinates[t.target][0] + coordinates[t.target][2]) / 2) ** 2 +
                                    (y2 - coordinates[t.target][1]) ** 2))
        target_counter = len(l)
        target_index = l.index(transition)
        h = y2 - y1
        x = (x3 + x4) / 2
        y = y2 - h / (target_counter + 1) - target_index * h / (target_counter + 1)
        return [(x1, y), (x, y), (x, y3)]
    else:
        l = generate_list('southeast')
        l.sort(
            key=lambda t: math.sqrt((x2 - (
                coordinates[t.target][0] + coordinates[t.target][2]) / 2) ** 2 +
                                    (y2 - coordinates[t.target][1]) ** 2))
        target_counter = len(l)
        target_index = l.index(transition)
        h = y2 - y1
        x = (x3 + x4) / 2
        y = y2 - h / (target_counter + 1) - target_index * h / (target_counter + 1)
        return [(x2, y), (x, y), (x, y3)]


def update_transitions_coordinates(transitions, coordinates):
    for transition in transitions:
        # First check if it is possible to draw directly a transition in with one line.
        source = transition.source
        target = transition.target
        x1, y1, x2, y2 = coordinates[source]
        x3, y3, x4, y4 = coordinates[target]
        if source != target:
            def generate_list():
                l = list(filter(lambda t: t.target == target, source.transitions)) + list(
                    filter(lambda t: t.target == source, target.transitions))
                l.sort(key=lambda t: t.source.name + t.target.name)
                return l

            same_target_counter = len(generate_list())
            same_target_index = generate_list().index(transition)
            direction = zone_of(source, target, coordinates)
            acc = acceptance_zone(source, target, 'horizontal', coordinates)
            # check if it is possible to join directly the target with one line
            if acc is not None:
                transition.polyline = []
                h = acc[1] - acc[0]
                y = acc[0] + h / (same_target_counter + 1) + same_target_index * h / (same_target_counter + 1)
                if direction == 'southwest' or direction == 'northwest':
                    transition.update_coordinates(start=(x1, y), end=(x4, y))
                else:
                    transition.update_coordinates(start=(x2, y), end=(x3, y))
            # vertical test
            else:
                acc = acceptance_zone(source, target, 'vertical', coordinates)
                if acc is not None:
                    transition.polyline = []
                    w = acc[1] - acc[0]
                    x = acc[0] + w / (same_target_counter + 1) + same_target_index * w / (same_target_counter + 1)
                    if direction == 'northeast' or direction == 'northwest':
                        transition.update_coordinates(start=(x, y1), end=(x, y4))
                    else:
                        transition.update_coordinates(start=(x, y2), end=(x, y3))
                elif source in target.ancestors:
                    # inner transition
                    transition.polyline = []
                    if source.axis == 'horizontal':
                        if target.parent.children.index(target) == 0:
                            transition.update_coordinates(start=(x1, (y3 + y4) / 2), end=(x3, (y3 + y4) / 2))
                        elif target.parent.childrent.index(target) == len(target.parent.children) - 1:
                            transition.update_coordinates(start=(x2, (y3 + y4) / 2), end=(x4, (y3 + y4) / 2))
                        elif zone_of(source, target, coordinates) == 'northeast' or zone_of(source, target,
                                                                                            coordinates) == 'northwest':
                            transition.update_coordinates(start=((x3 + x4) / 2, y1), end=((x3 + x4) / 2, y3))
                        else:
                            transition.update_coordinates(start=((x3 + x4) / 2, y2), end=((x3 + x4) / 2, y4))
                    else:
                        if target.parent.children.index(target) == 0:
                            transition.update_coordinates(start=((x3 + x4) / 2, y1), end=((x3 + x4) / 2, y3))
                        elif target.parent.childrent.index(target) == len(target.parent.children) - 1:
                            transition.update_coordinates(start=((x3 + x4) / 2, y2), end=((x3 + x4) / 2, y4))
                        elif zone_of(source, target, coordinates) == 'northwest' or zone_of(source, target,
                                                                                            coordinates) == 'southwest':
                            transition.update_coordinates(start=(x1, (y3 + y4) / 2), end=(x3, (y3 + y4) / 2))
                        else:
                            transition.update_coordinates(start=(x2, (y3 + y4) / 2), end=(x4, (y3 + y4) / 2))
                else:
                    # classic arrow
                    transition.polyline = classic_arrow(transition, coordinates)
        else:
            if source.zone == 'north':
                transition.polyline = [((x1 + x2) / 2, y1), ((x1 + x2) / 2, y1 - space),
                                       (x1 - space, y1 - space), (x1 - space, (y1 + y2) / 2),
                                       (x1, (y1 + y2) / 2)]
            elif source.zone == 'south':
                transition.polyline = [((x1 + x2) / 2, y2), ((x1 + x2) / 2, y2 + space),
                                       (x2 + space, y2 + space),
                                       (x2 + space, (y1 + y2) / 2), (x2, (y1 + y2) / 2)]
            elif source.zone == 'west':
                transition.polyline = [(x1, (y1 + y2) / 2), (x1 - space, (y1 + y2) / 2),
                                       (x1 - space, y1 - space), ((x1 + x2) / 2, y1 - space), ((x1 + x2) / 2, y1)]
            else:
                transition.polyline = [(x2, (y1 + y2) / 2), (x2 + space, (y1 + y2) / 2),
                                       (x2 + space, y2 + space), ((x1 + x2) / 2, y2 + space),
                                       ((x1 + x2) / 2, y2)]
    conflicts_checking(transitions, coordinates)


def conflicts_checking(transitions, coordinates):
    attractions_points = {}

    for transition in transitions:
        if (transition.conflicts_with_transitions(transitions) \
                or transition.conflicts_with_boxes(coordinates)) \
                and transition.source != transition.target:
            lower_common_ancestor = structures.box.lower_common_ancestor(transition.source, transition.target)
            n, e, s, w = compute_attraction_points(lower_common_ancestor, coordinates)
            if zone(transition.source, transition.target, coordinates) == 'west':
                x1, y1, x2, y2 = coordinates[transition.source]
                if x1 <= n[0]:
                    points = [min([n, s, w], key=lambda x: attractions_points.get(x, 0))]
                    attractions_points[points[-1]] = attractions_points.get(points[-1], 0) + 1
                    if points[-1] == w:
                        points = [(x1, (y1 + y2) / 2)]
                        w1, w2 = w
                        points += [(w1, (y1 + y2) / 2)]
                        # points += [w]
                        points += [min([n, s], key=lambda x: attractions_points.get(x, 0))]
                    if points[-1] == n:
                        if len(points) == 1:
                            points = [((x1 + x2) / 2, y1)]
                        n1, n2 = n
                        points += [(points[-1][0], n2)]
                        points += [n]
                    elif points[-1] == s:
                        if len(points) == 1:
                            points = [((x1 + x2) / 2, y2)]
                        s1, s2 = s
                        points += [(points[-1][0], s2)]
                        points += [s]
                else:
                    points = [min([n, s], key=lambda x: attractions_points.get(x, 0))]
                    attractions_points[points[-1]] = attractions_points.get(points[-1], 0) + 1
                    if points[-1] == n:
                        points = [(x1, (y1 + y2) / 2)]
                        n1, n2 = n
                        points += [(x1, n2)]
                        points += [n]
                    elif points[-1] == s:
                        points = [(x2, (y1 + y2) / 2)]
                        s1, s2 = s
                        points += [(x2, s2)]
                        points += [s]
                x1, y1, x2, y2 = coordinates[transition.target]
                mid = (x1 + x2) / 2
                a1, a2 = points[-1]
                b1, b2 = min([(mid, y1), (mid, y2)], key=lambda x: distance(points[-1], x))
                points += [(b1, a2), (b1, b2)]
            elif zone(transition.source, transition.target, coordinates) == 'east':
                x1, y1, x2, y2 = coordinates[transition.source]
                if x1 >= n[0]:
                    points = [min([n, s, e], key=lambda x: attractions_points.get(x, 0))]
                    attractions_points[points[-1]] = attractions_points.get(points[-1], 0) + 1
                    if points[-1] == e:
                        points = [(x2, (y1 + y2) / 2)]
                        e1, e2 = e
                        points += [(e1, (y1 + y2) / 2)]
                        # points += [e]
                        points += [min([n, s], key=lambda x: attractions_points.get(x, 0))]
                    if points[-1] == n:
                        if len(points) == 1:
                            points = [((x1 + x2) / 2, y1)]
                        n1, n2 = n
                        points += [(points[-1][0], n2)]
                        points += [n]
                    elif points[-1] == s:
                        if len(points) == 1:
                            points = [((x1 + x2) / 2, y2)]
                        s1, s2 = s
                        points += [(points[-1][0], s2)]
                        points += [s]
                else:
                    points = [min([n, s], key=lambda x: attractions_points.get(x, 0))]
                    attractions_points[points[-1]] = attractions_points.get(points[-1], 0) + 1
                    if points[-1] == n:
                        points = [(x1, (y1 + y2) / 2)]
                        n1, n2 = n
                        points += [(x1, n2)]
                        points += [n]
                    elif points[-1] == s:
                        points = [(x2, (y1 + y2) / 2)]
                        s1, s2 = s
                        points += [(x2, s2)]
                        points += [s]
                x1, y1, x2, y2 = coordinates[transition.target]
                mid = (x1 + x2) / 2
                a1, a2 = points[-1]
                b1, b2 = min([(mid, y1), (mid, y2)], key=lambda x: distance(points[-1], x))
                points += [(b1, a2), (b1, b2)]
            elif zone(transition.source, transition.target, coordinates) == 'north':
                x1, y1, x2, y2 = coordinates[transition.source]
                if y1 <= w[1]:
                    points = [min([n, w, e], key=lambda x: attractions_points.get(x, 0))]
                    attractions_points[points[-1]] = attractions_points.get(points[-1], 0) + 1
                    if points[-1] == n:
                        points = [((x1 + x2) / 2, y1)]
                        n1, n2 = n
                        points += [((x1 + x2) / 2, n2)]
                        # points += [n]
                        points += [min([e, w], key=lambda x: attractions_points.get(x, 0))]
                    if points[-1] == w:
                        if len(points) == 1:
                            points = [(x1, (y1 + y2) / 2)]
                        w1, w2 = w
                        points += [(w1, points[-1][1])]
                        points += [w]
                    elif points[-1] == e:
                        if len(points) == 1:
                            points = [(x2, (y1 + y2) / 2)]
                        e1, e2 = e
                        points += [(e1, points[-1][1])]
                        points += [e]
                else:
                    points = [min([w, e], key=lambda x: attractions_points.get(x, 0))]
                    attractions_points[points[-1]] = attractions_points.get(points[-1], 0) + 1
                    if points[-1] == w:
                        points = [((x2 + x2) / 2, y1)]
                        w1, w2 = w
                        points += [(w1, y1)]
                        points += [w]
                    elif points[-1] == e:
                        points = [((x1 + x2) / 2, y2)]
                        e1, e2 = e
                        points += [(e1, y2)]
                        points += [e]
                x1, y1, x2, y2 = coordinates[transition.target]
                mid = (y1 + y2) / 2
                a1, a2 = points[-1]
                b1, b2 = min([(x1, mid), (x2, mid)], key=lambda x: distance(points[-1], x))
                points += [(a1, b2), (b1, b2)]
            else:
                x1, y1, x2, y2 = coordinates[transition.source]
                if y1 >= w[1]:
                    points = [min([s, w, e], key=lambda x: attractions_points.get(x, 0))]
                    attractions_points[points[-1]] = attractions_points.get(points[-1], 0) + 1
                    if points[-1] == s:
                        points = [((x1 + x2) / 2, y2)]
                        s1, s2 = s
                        points += [((x1 + x2) / 2, s2)]
                        # points += [s]
                        points += [min([e, w], key=lambda x: attractions_points.get(x, 0))]
                    if points[-1] == w:
                        if len(points) == 1:
                            points = [(x1, (y1 + y2) / 2)]
                        w1, w2 = w
                        points += [(w1, points[-1][1])]
                        points += [w]
                    elif points[-1] == e:
                        if len(points) == 1:
                            points = [(x2, (y1 + y2) / 2)]
                        e1, e2 = e
                        points += [(e1, points[-1][1])]
                        points += [e]
                else:
                    points = [min([w, e], key=lambda x: attractions_points.get(x, 0))]
                    attractions_points[points[-1]] = attractions_points.get(points[-1], 0) + 1
                    if points[-1] == w:
                        points = [((x1 + x2) / 2, y1)]
                        w1, w2 = w
                        points += [(w1, y1)]
                        points += [w]
                    elif points[-1] == e:
                        points = [((x1 + x2) / 2, y2)]
                        e1, e2 = e
                        points += [(e1, y2)]
                        points += [e]
                x1, y1, x2, y2 = coordinates[transition.target]
                mid = (y1 + y2) / 2
                a1, a2 = points[-1]
                b1, b2 = min([(x1, mid), (x2, mid)], key=lambda x: distance(points[-1], x))
                points += [(a1, b2), (b1, b2)]
            transition.polyline = points


def compute_attraction_points(box, coordinates):
    x1, y1, x2, y2 = coordinates[box]
    y1 += box.header
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2
    return (mid_x, y1 + space / 2), (x2 - space / 2, mid_y), (mid_x, y2 - space / 2), (x1 + space / 2, mid_y)


def distance(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def zone(box1, box2, coordinates):
    x1, y1, x2, y2 = coordinates[box1]
    x3, y3, x4, y4 = coordinates[box2]
    x1, y1 = (x1 + x2) / 2, (y1 + y2) / 2
    x2, y2 = (x3 + x4) / 2, (y3 + y4) / 2
    if distance((x1, y1), (x2, y2)) == 0:
        return False
    cos = (x2 - x1) / distance((x1, y1), (x2, y2))
    sin = (y2 - y1) / distance((x1, y1), (x2, y2))
    if math.fabs(cos) >= math.sqrt(2) / 2:
        if cos >= 0:
            return 'west'
        else:
            return 'east'
    else:
        if sin >= 0:
            return 'north'
        else:
            return 'south'
