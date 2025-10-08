FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies for OpenCV, MediaPipe and build tools
RUN yum install -y \
    gcc \
    gcc-c++ \
    make \
    mesa-libGL \
    libglib2.0 \
    glib2 \
    libSM \
    libXrender \
    libXext \
    wget \
    && yum clean all

# Copy requirements
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download MediaPipe models during build
RUN python3 -c "import mediapipe as mp; mp.solutions.pose.Pose(model_complexity=1)" || true

# Copy application code
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Create __init__.py if it doesn't exist
RUN touch ${LAMBDA_TASK_ROOT}/src/__init__.py

# Set environment variable to help with shared library loading
ENV LD_LIBRARY_PATH=/var/lang/lib:/lib64:/usr/lib64:/var/runtime:/var/task:/opt/lib

# Set the handler
CMD ["src.api.handler"]
