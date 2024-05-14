import numpy as np
import cv2
from PIL import Image, ImageChops
from scipy.interpolate import make_interp_spline
import networkx as nx
import os


def ComputeSegMap_SegFormer(image):
    return Image.open(f'Simulation/Seg_map/{image}_sm.png')


def ComputeDepthmap(image):
    return Image.open(f'Simulation/Depth_map/{image}_dm.png')


"""
    Computed based on the depth map and the segmentation map. The probability of
flying over a pixel is calculated as the ratio of the pixel value (uint8) and 255
"""


def ComputeProbMap(seg_map, dep_map):
    # Clarifying the boundaries of objects on the segmentation map and overlapping random outliers
    seg = np.asarray(seg_map)
    seg = cv2.GaussianBlur(seg, (9, 9), 0)

    edge = cv2.Canny(seg, 10, 180, L2gradient=True)
    contours, _ = cv2.findContours(
        edge.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    smoothed_contours = [cv2.approxPolyDP(
        cnt, 0.1 * cv2.arcLength(cnt, True), True) for cnt in contours]

    for contour in contours:
        mask = np.zeros(seg.shape[:2], dtype="uint8")
        cv2.drawContours(mask, [contour], -1, 255, -1)

        masked = cv2.bitwise_and(seg, seg, mask=mask)
        masked = masked[mask != 0]
        values, counts = np.unique(masked, return_counts=True)
        dominant_color = values[counts.argmax()]

        cv2.drawContours(seg, [contour], -1,
                         dominant_color.tolist(), cv2.FILLED)

    dep = np.asarray(dep_map)

    # The probability map will be inverted later, therefore, in a place with a minimum probability of flight, the pixel value is 255
    prob = np.multiply(dep/np.max(dep), seg)
    prob_map = np.full((prob.shape[0], prob.shape[1]), 255).astype('uint8')

    prob_map[prob < np.max(prob)*0.8] = 230
    prob_map[prob < np.max(prob)*0.7] = 200
    prob_map[prob < np.max(prob)*0.6] = 180
    prob_map[prob < np.max(prob)*0.5] = 150
    prob_map[prob < np.max(prob)*0.4] = 127
    prob_map[prob < np.max(prob)*0.3] = 100
    prob_map[prob < np.max(prob)*0.2] = 76
    prob_map[prob < np.max(prob)*0.1] = 30

    return Image.fromarray(prob_map.astype('uint8'))


"""
    In the graph, points that are 9 pixels apart are selected according to a given grid.
These points become nodes in the graph. The weight of a branch is calculated as the average
value of the pixels in a 9x9 square that is plotted between the two points.
"""


def Compute_grapf(prob_map):
    prob_map = ImageChops.invert(prob_map)
    img = np.asarray(prob_map)
    graph_side = 9
    alpha = graph_side // 2
    beta = graph_side

    G = nx.Graph()

    for y in range(graph_side // 2, graph_side*(img.shape[0]//graph_side - 1), graph_side):
        for x in range(graph_side // 2, graph_side*(img.shape[1]//graph_side - 1), graph_side):

            main_node = f'{x},{y}'

            righ_node = f'{x+graph_side},{y}'
            down_node = f'{x},{y+graph_side}'
            diag_node = f'{x+graph_side},{y+graph_side}'

            right = img[(y-alpha):(y+alpha+1), (x+1):(x+beta+1)]
            down = img[(y+1):(y+beta+1), (x-alpha):(x+alpha+1)]
            diag = img[(y+1):(y+beta+1), (x+1):(x+beta+1)]

            if x > graph_side:
                diag2_node = f'{x-graph_side},{y+1}'
                diag2 = img[(y+1):(y+beta+1), (x-beta):(x)]
                G.add_edge(main_node, diag2_node,
                           weight=int(np.average(diag2)))

            G.add_edge(main_node, righ_node, weight=int(np.average(right)))
            G.add_edge(main_node, down_node, weight=int(np.average(down)))
            G.add_edge(main_node, diag_node, weight=int(np.average(diag)))

    return G


def smooth_path(path):
    x_arr = []
    y_arr = []
    res = []

    # Division into X and Y coordinates
    for item in path:
        x, y = item.split(',')
        x_arr.append(int(x))
        y_arr.append(int(y))

    x = np.array(x_arr)
    y = np.array(y_arr)

    num_of_points = int(x.size/5)
    # The representation of a path of flight (a function defined as y(x)) in terms of parametric equations x(t) and y(t),
    # where t represents some increasing variable, in this case, the index in an array.
    # This is done to avoid interpolation errors caused by duplicated x-values.
    t = np.arange(0, int(x.size))

    xt = make_interp_spline(t, x)
    yt = make_interp_spline(t, y)

    tn = np.linspace(t.min(), t.max(), num_of_points).astype(int)

    x_n = xt(tn).astype(int)
    y_n = yt(tn).astype(int)

    for i in range(num_of_points):
        res.append(f'{x_n[i]},{y_n[i]}')
    return res


def Compute_path_betwen_2_points(grapf, first_point, second_point):
    # Find the nearest points to the specified ones, which are graph nodes, and reinitialize the points.
    repoint = tuple(map(int, first_point.split(',')))
    repoint_f = (repoint[0]//9)*9+4
    repoint_s = (repoint[1]//9)*9+4
    first_point = f'{repoint_f},{repoint_s}'

    repoint = tuple(map(int, second_point.split(',')))
    repoint_f = (repoint[0]//9)*9+4
    repoint_s = (repoint[1]//9)*9+4
    second_point = f'{repoint_f},{repoint_s}'
    # Finding the shortest path and its length
    path = nx.shortest_path(grapf, first_point, second_point, weight='weight')
    length = nx.shortest_path_length(
        grapf, first_point, second_point, weight='weight')
    return smooth_path(path), length


def draw_path(image, path_of_flight):
    coordinates = [tuple(map(int, point.split(',')))
                   for point in path_of_flight]
    img = np.asarray(image)
    img = np.copy(img)
    for i in range(len(path_of_flight)-1):
        cv2.line(img, coordinates[i], coordinates[i+1], (255, 0, 0), 10)
    return Image.fromarray(img)


def ComputeFlightMap(image, image_path=None):
    image = image_path
    image = os.path.splitext(os.path.basename(image_path))[0]
    SM = ComputeSegMap_SegFormer(image)
    DM = ComputeDepthmap(image)
    PM = ComputeProbMap(SM, DM)
    Grapf = Compute_grapf(PM)
    return Grapf
