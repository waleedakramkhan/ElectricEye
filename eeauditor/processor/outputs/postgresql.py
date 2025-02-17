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
import sys
import os
import psycopg2 as psql
from processor.outputs.output_base import ElectricEyeOutput


@ElectricEyeOutput
class PostgresProvider(object):
    __provider__ = "postgres"

    def __init__(self):
        ssm = boto3.client("ssm")
        # Username
        try:
            psqlUsername = os.environ["POSTGRES_USERNAME"]
        except KeyError:
            psqlUsername = "placeholder"
        # DB Name
        try:
            eePsqlDbName = os.environ["ELECTRICEYE_POSTGRESQL_DB_NAME"]
        except KeyError:
            eePsqlDbName = "placeholder"
        # DB Endpoint
        try:
            dbEndpoint = os.environ["POSTGRES_DB_ENDPOINT"]
        except KeyError:
            dbEndpoint = "placeholder"
        # DB Port
        try:
            dbPort = os.environ["POSTGRES_DB_PORT"]
        except KeyError:
            dbPort = "placeholder"
        # Secret Parameter
        try:
            psqlRdsPwSsmParamName = os.environ["POSTGRES_PASSWORD_SSM_PARAM_NAME"]
        except KeyError:
            psqlRdsPwSsmParamName = "placeholder"
        

        if (
            psqlUsername or 
            eePsqlDbName or 
            dbEndpoint or 
            dbPort or 
            psqlRdsPwSsmParamName
        ) == ("placeholder" or None):
            print('Either the required RDS Information was not provided, or the "placeholder" values were kept')
            sys.exit(2)
        else:
            # Retrieve and Decrypt DB PW from SSM
            psqlDbPw = ssm.get_parameter(Name=psqlRdsPwSsmParamName, WithDecryption=True)["Parameter"]["Value"]

            self.db_endpoint = dbEndpoint
            self.db_port = dbPort
            self.db_username = psqlUsername
            self.db_password = psqlDbPw
            self.db_name = eePsqlDbName

    def write_findings(self, findings: list, **kwargs):
        print(f"Writing {len(findings)} results to PostgreSQL")
        if (self.db_endpoint and self.db_port and self.db_username and self.db_password and self.db_name):
            try:
                # Connect to DB and create a Cursor
                engine = psql.connect(
                    database=self.db_name,
                    user=self.db_username,
                    password=self.db_password,
                    host=self.db_endpoint,
                    port=self.db_port
                )
                cursor = engine.cursor()
                
                # drop previously existing tables
                cursor.execute("""DROP TABLE IF EXISTS electriceye_findings""")
                engine.commit()
                
                # Create a new table for the ElectricEye findings. Everything is set as Text
                cursor.execute("""CREATE TABLE IF NOT EXISTS electriceye_findings( schemaversion TEXT, findingid TEXT, awsaccountid TEXT, productarn TEXT, generatorid TEXT, types TEXT, createdat TEXT, severitylabel TEXT, confidence TEXT, title TEXT, description TEXT, resourcetype TEXT, resourceid TEXT, resourceregion TEXT, resourcepartition TEXT, compliancestatus TEXT, compliancecontrols TEXT, workflowstatus TEXT, recordstate TEXT);""")

                for finding in findings:
                    # Basic parsing of ASFF to prepare for INSERT into PSQL
                    try:
                        awsaccountid = str(finding['AwsAccountId'])
                    except Exception as e:
                        if str(e) == "'AwsAccountId'":
                            awsaccountid = str(finding['awsAccountId'])
                        else:
                            continue
                    schemaversion = str(finding['SchemaVersion'])
                    findingid = str(finding['Id'])
                    productarn = str(finding['ProductArn'])
                    generatorid = str(finding['GeneratorId'])
                    types = str(finding['Types'][0])
                    createdat = str(finding['CreatedAt'])
                    severitylabel = str(finding['Severity']['Label'])
                    #TODO: Find which findings aren't mapped...
                    try:
                        confidence = str(finding['Confidence'])
                    except Exception:
                        confidence = '99'
                    title = str(finding['Title'])
                    description = str(finding['Description'])
                    resourcetype = str(finding['Resources'][0]['Type'])
                    resourceid = str(finding['Resources'][0]['Id'])
                    resourceregion = str(finding['Resources'][0]['Region'])
                    resourcepartition = str(finding['Resources'][0]['Partition'])
                    compliancestatus = str(finding['Compliance']['Status'])
                    #TODO: Find which findings aren't mapped...
                    try:
                        compliancecontrols = str(finding['Compliance']['RelatedRequirements'])
                    except Exception:
                        compliancecontrols = str('[]')
                    workflowstatus = str(finding['Workflow']['Status'])
                    recordstate = str(finding['RecordState'])

                    # Write into Postgres
                    cursor.execute("INSERT INTO electriceye_findings( schemaversion, findingid, awsaccountid, productarn, generatorid, types, createdat, severitylabel, confidence, title, description, resourcetype, resourceid, resourceregion, resourcepartition, compliancestatus, compliancecontrols, workflowstatus, recordstate) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);", (schemaversion, findingid, awsaccountid, productarn, generatorid, types, createdat, severitylabel, confidence, title, description, resourcetype, resourceid, resourceregion, resourcepartition, compliancestatus, compliancecontrols, workflowstatus, recordstate))
                
                # commit the changes
                engine.commit()
                # close communication with the postgres server (rds)
                cursor.close()

            except psql.OperationalError:
                print("Cannot connect to PostgreSQL! Review your Security Group settings and/or information provided to connect")
                exit(2)
            except Exception:
                print("Another exception found " + Exception)
                exit(2)
        else:
            raise ValueError("Missing credentials or database parameters")