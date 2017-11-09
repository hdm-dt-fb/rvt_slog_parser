import os.path as op
from bokeh.plotting import figure, save, output_file
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, HoverTool
from bokeh.palettes import viridis
import pandas as pd


def build_graph_html(dataframe, project_code):

    graph_title = project_code + "_rvt_sessions"

    html_path = op.join(op.dirname(__file__), "html")
    output_path = op.join(html_path, project_code + "_rvt_sessions.html")
    output_file(output_path, title=graph_title)

    colors = viridis(len(dataframe["users"]))
    hover = HoverTool(tooltips=[("name", "@name"),
                                ("time", "@time"),
                                ("count", "@count"),
                                ])
    tools_opt = ["resize", "hover", "save", "pan", "wheel_zoom", "reset"]  # hover not active yet
    graph_opt = dict(width=900, x_axis_type="datetime",
                     toolbar_location="left", tools=tools_opt, toolbar_sticky=False,
                     background_fill_alpha=0, border_fill_alpha=0)

    sessions = figure(title=graph_title, y_range=list(dataframe["users"].unique()), **graph_opt)

    # session segments
    # sessions.segment(dataframe["starts"], dataframe["users"],
    #                  dataframe["ends"], dataframe["users"],
    #                  line_width=2, line_color=colors,
    #                  )
    sessions.hbar(y=dataframe["users"],
                  left=dataframe["starts"],
                  right=dataframe["ends"],
                  height=0.5, color=colors
                  )

    # link loads segments
    # --

    # sync points
    # sessions.circle(df["starts"], users, size=15, fill_color="orange")

    # request matrix

    # sync fail

    style_plot(sessions)
    save(sessions)


def style_plot(plot):
    # axis styling, legend styling
    plot.outline_line_color = None
    plot.axis.axis_label = None
    plot.axis.axis_line_color = None
    plot.axis.major_tick_line_color = None
    plot.axis.minor_tick_line_color = None
    plot.ygrid.grid_line_color = None
    plot.xgrid.grid_line_color = None
    plot.xaxis.formatter = DatetimeTickFormatter(hours=["%H:%M - %d %b %Y"],
                                                 days=["%H:%M - %d %b %Y"],
                                                 months=["%H:%M - %d %b %Y"],
                                                 years=["%H:%M - %d %b %Y"]
                                                 )
    plot.legend.location = "top_left"
    plot.legend.border_line_alpha = 0
    plot.legend.background_fill_alpha = 0
    plot.title.text_font_size = "14pt"
    return plot


def dict_to_df(df_dict):
    df = pd.DataFrame()
    df["users"] = df_dict["user"]
    df["starts"] = df_dict["start"]
    df["ends"] = df_dict["end"]
    df["starts"] = pd.to_datetime(df["starts"])
    df["ends"] = pd.to_datetime(df["ends"])
    df = df[df.ends.notnull()]
    # print(df)
    return df


if __name__ == "__main__":
    build_graph_html(None, "999_test")
