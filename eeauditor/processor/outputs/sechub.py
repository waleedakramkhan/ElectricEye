#This file is part of ElectricEye.
#SPDX-License-Identifier: Apache-2.0

#Licensed to the Apache Software Foundation (ASF) under one
#or more contributor license agreements.  See the NOTICE file
#distributed with this work for additional information
#regarding copyright ownership.  The ASF licenses this file
#to you under the Apache License, Version 2.0 (the
#"License"); you may not use this file except in compliance
#with the License.  You may obtain a copy of the License at

#http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing,
#software distributed under the License is distributed on an
#"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#KIND, either express or implied.  See the License for the
#specific language governing permissions and limitations
#under the License.
import boto3
from processor.outputs.output_base import ElectricEyeOutput

@ElectricEyeOutput
class SecHubProvider(object):
    __provider__ = "sechub"

    def write_findings(self, findings: list, **kwargs):
        print(f"Writing {len(findings)} results to SecurityHub")
        if findings:
            sechub = boto3.client("securityhub")
            # write to securityhub in batches of 100
            for i in range(0, len(findings), 100):
                sechub.batch_import_findings(Findings=findings[i : i + 100])
        return