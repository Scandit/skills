/* gst_pipeline.c - conveyor camera: frames arrive as NV12 from a GStreamer appsink.
 * Build: gcc -O2 -std=c99 -o conveyor gst_pipeline.c $(pkg-config --cflags --libs gstreamer-app-1.0 gstreamer-video-1.0)
 */
#include <stdio.h>
#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <gst/video/video.h>

int main(int argc, char **argv) {
    gst_init(&argc, &argv);
    GError *err = NULL;
    GstElement *pipeline = gst_parse_launch(
            "v4l2src device=/dev/video0 ! video/x-raw,format=NV12,width=1920,height=1080 ! appsink name=sink", &err);
    if (!pipeline) { fprintf(stderr, "%s\n", err->message); g_clear_error(&err); return 1; }
    GstAppSink *sink = GST_APP_SINK(gst_bin_get_by_name(GST_BIN(pipeline), "sink"));
    gst_element_set_state(pipeline, GST_STATE_PLAYING);
    for (;;) {
        GstSample *sample = gst_app_sink_pull_sample(sink);
        if (!sample) break;
        GstVideoInfo info;
        GstMapInfo map;
        GstBuffer *buffer = gst_sample_get_buffer(sample);
        if (gst_video_info_from_caps(&info, gst_sample_get_caps(sample)) && gst_buffer_map(buffer, &map, GST_MAP_READ)) {
            /* TODO: scan the NV12 frame in map.data with the Scandit SDK */
            gst_buffer_unmap(buffer, &map);
        }
        gst_sample_unref(sample);
    }
    gst_element_set_state(pipeline, GST_STATE_NULL);
    gst_object_unref(sink);
    gst_object_unref(pipeline);
    return 0;
}
