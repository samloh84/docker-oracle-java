FROM samloh84/centos:7

ARG VENDOR=oracle
ARG PRODUCT=jdk
ARG PRODUCT_VERSION=8u131
ARG TEMP_DIR_ROOT=/tmp/${VENDOR}-${PRODUCT}
ARG TEMP_DIR=/${TEMP_DIR_ROOT}/${PRODUCT_VERSION}
ARG INSTALL_DIR_ROOT=/usr/java
ARG INSTALL_DIR=${INSTALL_DIR_ROOT}/jdk1.8.0_131

ARG JDK_INSTALL_RPM_URL="http://download.oracle.com/otn-pub/java/jdk/8u131-b11/d54c1d3a095b4ff2b6607d096fa80163/jdk-8u131-linux-x64.rpm"
ARG JDK_INSTALL_RPM=jdk-${PRODUCT_VERSION}-linux-x64.rpm
ARG JDK_INSTALL_RPM_SHA256SUM=3d1e8cc66f4fd77acef6093329d5dd95bd06e4a03926c52df794f311a0c093f8
ARG JCE_POLICY_ZIP_URL="http://download.oracle.com/otn-pub/java/jce/8/jce_policy-8.zip"
ARG JCE_POLICY_ZIP=jce_policy-8.zip
ARG JCE_POLICY_ZIP_SHA256SUM=f3020a3922efd6626c2fff45695d527f34a8020e938a49292561f18ad1320b59
ARG JCE_POLICY_ZIP_JAR_GLOB=UnlimitedJCEPolicyJDK8/*.jar

USER ${ROOT_UID}

RUN \
yum-install unzip && \
mkdir -p ${TEMP_DIR} && \
pushd ${TEMP_DIR} && \
curl -LjSs -H "Cookie: oraclelicense=accept-securebackup-cookie" \
${JDK_INSTALL_RPM_URL} -o ${JDK_INSTALL_RPM} && \
curl -LjSs -H "Cookie: oraclelicense=accept-securebackup-cookie" \
${JCE_POLICY_ZIP_URL} -o ${JCE_POLICY_ZIP} && \
echo "${JDK_INSTALL_RPM_SHA256SUM}  ${JDK_INSTALL_RPM}" | sha256sum -c - && \
echo "${JCE_POLICY_ZIP_SHA256SUM}  ${JCE_POLICY_ZIP}" | sha256sum -c - && \
yum-install ${TEMP_DIR}/${JDK_INSTALL_RPM} && \
unzip -qq ${JCE_POLICY_ZIP} -d ${TEMP_DIR} && \
mv -f ${TEMP_DIR}/${JCE_POLICY_ZIP_JAR_GLOB} ${INSTALL_DIR}/jre/lib/security && \
popd && \
rm -rf ${TEMP_DIR_ROOT}

ENV JAVA_HOME ${INSTALL_DIR}
ENV PATH ${JAVA_HOME}/bin:${JAVA_HOME}/jre/bin:${PATH}

USER ${APP_UID}
