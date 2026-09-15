FROM alibaba-cloud-linux-3-registry.cn-hangzhou.cr.aliyuncs.com/alinux3/python:3.11.1
# 设置时区
ENV TimeZone=Asia/Beijing
RUN ln -snf /usr/share/zoneinfo/$TimeZone /etc/localtime && echo $TimeZone > /etc/timezone

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN yum install -y \
    gcc \
    python3-devel \
    mysql-devel \
    openssl-devel \
    libffi-devel \
&& yum clean all

# 👇 定义镜像源参数
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt /app/requirements.txt

# 👇 使用参数，代码更简洁
#RUN pip install --no-cache-dir -r requirements.txt -i $PIP_INDEX_URL
#RUN pip install --no-cache-dir -r requirements.txt -i $PIP_INDEX_URL
#RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
