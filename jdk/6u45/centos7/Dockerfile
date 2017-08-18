FROM samloh84/centos:7

ARG VENDOR=oracle
ARG PRODUCT=oracle-java-jdk
ARG PRODUCT_VERSION=6u45
ARG TEMP_DIR_ROOT=/tmp/${VENDOR}-${PRODUCT}
ARG TEMP_DIR=/${TEMP_DIR_ROOT}/${PRODUCT_VERSION}
ARG INSTALL_DIR_ROOT=/usr/java
ARG INSTALL_DIR=${INSTALL_DIR_ROOT}/jdk1.6.0_45
ARG ORACLE_USERNAME
ARG ORACLE_PASSWORD
ARG JDK_INSTALL_RPM_BIN_URL=http://download.oracle.com/otn/java/jdk/6u45-b06/jdk-6u45-linux-x64-rpm.bin
ARG JDK_INSTALL_RPM_BIN=jdk-6u45-linux-x64-rpm.bin

ARG JCE_POLICY_ZIP_URL=http://download.oracle.com/otn-pub/java/jce_policy/6/jce_policy-6.zip
ARG JCE_POLICY_ZIP=jce_policy-6.zip

USER ${ROOT_UID}

COPY downloader.py ${TEMP_DIR}/

RUN \
yum-install unzip && \
mkdir -p ${TEMP_DIR} && \
pushd ${TEMP_DIR} && \
python2 downloader.py \
--url ${JDK_INSTALL_RPM_BIN_URL} \
--filename ${JDK_INSTALL_RPM_BIN} \
--username ${ORACLE_USERNAME} \
--password ${ORACLE_PASSWORD} && \
chmod +x ${JDK_INSTALL_RPM_BIN} && \
./${JDK_INSTALL_RPM_BIN} && \

python2 downloader.py \
--url ${JCE_POLICY_ZIP_URL} \
--filename ${JCE_POLICY_ZIP} \
--username ${ORACLE_USERNAME} \
--password ${ORACLE_PASSWORD} && \
unzip -qq ${JCE_POLICY_ZIP} -d ${TEMP_DIR}/jce && \
find ${TEMP_DIR}/jce -name "*.jar" -print0 | xargs -0 mv -t ${INSTALL_DIR}/jre/lib/security && \
popd && \
rm -rf ${TEMP_DIR_ROOT}

ENV JAVA_HOME ${INSTALL_DIR}
ENV PATH ${JAVA_HOME}/bin:${JAVA_HOME}/jre/bin:${PATH}

USER ${APP_UID}