import os
from Prob_map import ComputeFlightMap, Compute_path_betwen_2_points, draw_path
import tkinter as tk
from tkinter import filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageDraw
import datetime
import os

TEST = True


class ImageApp(tk.Tk):
    def __init__(self, root):
        self.root = root

        self.root = root
        self.root.geometry('1280x800')
        self.image_path = None
        self.image = None

        self.points = []  # coordinates of the points in the image
        self.grapf = None  # graph based on the image

        self.path_of_flight = None
        self.length_of_flight = None

        # Menu
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)

        # File menu
        self.file_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Open", command=self.open_image)
        self.file_menu.add_command(label="Save", command=self.save_image)
        self.menu.add_command(label="Compute path", command=self.compute_path)
        self.menu.add_command(label="Clear image", command=self.clear_image)
        self.menu.add_command(label="Delete image", command=self.delete_image)

        # Image display area
        self.figure = Figure(figsize=(12, 9), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('white')
        self.canvas.draw()

        # Bind click event
        self.canvas.mpl_connect('button_press_event', self.on_click)

    def open_image(self):
        """
            When a user clicks on the button, an image is displayed in the designated area.
        If the area already contains an image, it will be replaced with the new one.
        Upon clicking, all information regarding the image is reset to its original state,
        and only then is information about the newly displayed image entered.
        """
        self.image_path = None
        self.points = []
        self.grapf = None
        self.path_of_flight = None
        self.image = None
        self.length_of_flight = None

        self.image_path = filedialog.askopenfilename()

        if self.image_path:
            if TEST:
                split_path = self.image_path.split(os.sep)
                start_index = split_path.index('Simulation')
                test_dir_path = os.sep.join(
                    split_path[start_index:start_index+2])
                if test_dir_path != 'Simulation/Images':
                    messagebox.showwarning("Warning", "The mode of operation for this system is simulation. During this mode, the depth map and segmentation map will not be calculated on the fly, but instead will be pre-computed using the attached IPython notebook. To ensure proper operation, please select an image from the ""Simulation/Images"" directory.")
                    self.image_path = None
                    return
            self.image = Image.open(self.image_path).convert('RGB')
            self.ax.clear()
            self.ax.imshow(self.image)
            self.canvas.draw()

    def save_image(self):
        """
            If there is a built path between the points, it creates: an image and a path.
        The information is stored in the Results directory.
        """
        if self.path_of_flight:
            if not os.path.isdir('Results'):
                os.mkdir('Results')

            current_time = datetime.datetime.now()

            name_of_dir = f'{os.path.splitext(os.path.basename(self.image_path))[0]}-{current_time.day}-{
                current_time.month}-{current_time.year}-{current_time.hour}:{current_time.minute}'
            os.mkdir(f'Results/{name_of_dir}')
            self.image.save(f'Results/{name_of_dir}/image_with_path.png')
            with open(f'Results/{name_of_dir}/path_of_flight.txt', "w") as output:
                output.write(str(self.path_of_flight))
            pass
        else:
            messagebox.showerror("Error", "No data to save.")

    def compute_path(self):
        """
            If there are two points in the image and a path between them has not been established,
        the optimal flight path is calculated and displayed in the image.
        """
        if self.path_of_flight == None:
            if len(self.points) == 2:
                if self.grapf == None:
                    self.grapf = ComputeFlightMap(Image.open(self.image_path).convert('RGB'),
                                                  self.image_path)
                self.path_of_flight, self.length_of_flight = Compute_path_betwen_2_points(
                    self.grapf, self.points[0], self.points[1])
                self.image = draw_path(self.image, self.path_of_flight)
                self.ax.clear()
                self.ax.imshow(self.image)
                self.canvas.draw()

            else:
                messagebox.showwarning("Warning", "Please select two points.")
        else:
            messagebox.showwarning("Warning", "Clear the image first")

    def clear_image(self):
        """
            Clears all the points marked on the image and the built path,
        returns the image to its original state.
        """
        self.ax.clear()
        if self.image_path:
            self.image = Image.open(self.image_path).convert('RGB')
            self.ax.imshow(self.image)
        else:
            self.ax.set_facecolor('white')
        self.canvas.draw()
        self.points = []
        self.path_of_flight = None
        self.length_of_flight = None

    def delete_image(self):
        """
            Clears the image output area - returns a white background.
        Deletes all information about the image.
        """

        self.ax.clear()
        self.ax.set_facecolor('white')
        self.canvas.draw()

        self.image_path = None
        self.points = []
        self.grapf = None
        self.path_of_flight = None
        self.image = None
        self.length_of_flight = None

    def on_click(self, event):
        """
            When you click on an image that does not have a path, it adds a point to it.
        Only two points are stored in memory. When a new point is added, the oldest
        of the two built points is deleted.
        """
        if self.path_of_flight == None:
            if event.xdata is not None and event.ydata is not None and self.image is not None:

                if len(self.points) >= 2:
                    self.points.pop(0)

                self.points.append(f'{int(event.xdata)},{int(event.ydata)}')

                self.image = Image.open(self.image_path).convert('RGB')
                draw = ImageDraw.Draw(self.image)

                for point in self.points:
                    center = tuple(map(int, point.split(',')))
                    draw.ellipse((center[0], center[1],
                                  center[0]+10, center[1]+10),
                                 fill='red', outline='red',
                                 width=1)
                self.ax.clear()
                self.ax.imshow(self.image)
                self.canvas.draw()
            else:
                messagebox.showwarning("Warning", "Please select image")
        else:
            messagebox.showwarning("Warning", "Clear the image first")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageApp(root)
    root.mainloop()
