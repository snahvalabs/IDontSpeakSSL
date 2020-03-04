#!/usr/bin/env python3

from idontspeakssl.common.utils  import prepare_output_directory
from idontspeakssl.common.printer  import print_start_message
from idontspeakssl.modules.idontspeakssl_scanner import IDontSpeaksSSLScanner
import os,  mmap, re, base64, sys, socket, ssl, shutil, time
from termcolor import colored, cprint
from os import listdir
from os.path import isfile, join

import click


findingConfig = {}

    
def writeResult(filename,ip):
    with open(filename, "a") as resfile:
        resfile.write(ip)

def analyze(findingType, folder, data, scandir, ip):
    global findingConfig
    for finding in (findingConfig[findingType]).keys():
        if re.search(str(base64.b64decode(((findingConfig[findingType])[finding])[1]),'utf-8')  , data):
            writeResult("{}/{}/{}".format(scandir,folder,((findingConfig[findingType])[finding])[0],folder),"{}\n".format(ip))

def AnalyzeCertificates(folder, data, scandir, ip):
    ###  Certificates Check
    try:
        Days = int((re.findall('Certificate Validity \(UTC\) +(?:(\d+)|expired)', data))[0])
        if(Days > 825):
            writeResult("{}/{}/{}".format(scandir,folder,'TooLongCetificateValidity.txt'),"{}\t{} days\n".format(ip,Days))
    except:
        pass
    if(len(re.findall('Issuer +(.+)', data))>0):
        Issuer = (re.findall('Issuer +(.+)', data))[0]
        writeResult("{}/{}/{}".format(scandir,folder,'Issuers.txt'),"{}\t\t\t{}\n".format(ip.strip(), Issuer))

def AnalyzeScanFile(scandir):
    print()
    cprint("[-] Starting analyzing testssl.sh result files", 'blue')
    scanFiles = [f for f in listdir("{}/TestSSLscans".format(scandir)) if isfile(join("{}/TestSSLscans".format(scandir), f))]
    for scanFile in scanFiles:
            with open("{}/TestSSLscans/{}".format(scandir,scanFile), 'r') as scan:
                data = scan.read()
                # the scanFile[:-4] to remove the .txt
                analyze('Protocols', 'Protocols', data, scandir, scanFile[:-4])
                analyze('Ciphers', 'CipherSuites', data, scandir, scanFile[:-4])
                analyze('Flaws', 'Flaws', data, scandir, scanFile[:-4])
                analyze('Certificates', 'Certificates', data, scandir, scanFile[:-4])
                analyze('Configurations', 'Configurations', data, scandir, scanFile[:-4])
                AnalyzeCertificates('Certificates',data, scandir, scanFile[:-4])
    cprint("[+] Analyze done", 'blue')

def checkTargets(targetFile, targetList, scanDir):
    if ( not (targetFile or targetList)):
        return False
    if(targetFile):
        if(targetList):
            shutil.copyfile(targetFile, "{}/scope.txt".format(scanDir))
        else:
            if(os.path.exists(targetFile)):
                shutil.copyfile(targetFile, "{}/scope.txt".format(scanDir))
                return "{}/scope.txt".format(scanDir)
            else:
                cprint("[-] Target file doesn't exist", 'red')
                return False
    with open("{}/scope.txt".format(scanDir), "a") as targets:
        for target in targetList:
            targets.write("{}\n".format(target))
    return "{}/scope.txt".format(scanDir)

def file_to_target_list(target_file_path):
    target_list = []
    with open(target_file_path,'r') as target_file:
        for target in target_file:
            target =target.strip()
            if target !="":
                target_and_port = target.split(":")
                if(len(target_and_port)==1):
                    target_and_port.append("443")
                target_list.append({
				"host":target_and_port[0],
				"port":target_and_port[1],
				"proto":None
				#"proto":target_and_port[2] will need to be updated once nmap integration will be done
				})
    return  target_list

def string_to_target_list(target_string):
	full_target_list = []
	for target in target_string.split(","):
		if target !="":
			target_and_port = target.split(":")    
			if len(target_and_port)==1:
				target_and_port.append("443")
			full_target_list.append({
				"host":target_and_port[0],
				"port":target_and_port[1],
				"proto":None
				#"proto":target_and_port[2] will need to be updated once nmap integration will be done
				})
	return full_target_list

def prepare_target_list(target_file_path=None, target_string=None, nmap_path=None):
	full_target_list=[]
	if(target_file_path):
		temp_target_list = file_to_target_list(target_file_path)
		if temp_target_list:
			full_target_list += temp_target_list
	if target_string!=None:
		temp_target_list = string_to_target_list(target_string)
		if temp_target_list:
			full_target_list += temp_target_list
	return full_target_list


def generateList(scopePath):
    targetList = []
    with open(scopePath, "r") as targets:
        for target in targets:
            target=(target.strip()).split(":")
            if target[1]=="":
                targetList.append([target[0],"443"])
            else:
                targetList.append([target[0],target[1]])
    return targetList

def clearFolder(path):
    if(os.path.isdir(path)):
        for f in os.listdir(path):
            if(f != "SecureClientInitiatedRenegotiation.txt"):
                os.remove("{}/{}".format(path, f))

def generateReportFromScan(path):
    # Implement checks on file exist and might need to remove the generated
    targetlist = generateList("{}/scope.txt".format(path))
    config()
    clearAnalyzeFolder(path)
    AnalyzeScanFile(path)
    report = Report(path, targetlist)
    report.createReport()

def run_scanner(output_directory, target_file, target_string, nb_worker, report_format):
	print_start_message()
	full_target_list = prepare_target_list(target_file, target_string)
	result_directory = prepare_output_directory(output_directory, full_target_list)
	scanner = IDontSpeaksSSLScanner(result_directory, full_target_list, nb_worker)
	scanner.run()
	#AnalyzeScanFile(scandir)
	#report = Report(scandir, targetlist)
	#report.createReport()

def print_help_msg(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))

@click.command()
@click.option('-f', 'target_file', help='File containing taget IPs or domain names list, one per line', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True))
@click.option('-i', '--ip', 'target_string', help='List of taget IPs or domain names')
@click.option('-o', '--output', 'output', help='Output directory where scans will be saved', type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True), required=True)
@click.option('-w', 'nb_worker', help='number of workers. Number of scan to run at the same time. By default defined to 8', default=8)
@click.option('-r', 'status_file_path', help='Generate a report from scan files. Take a path to the scan folder.')
@click.option("--format", "report_format", multiple=True, default=["web",'textile'])
def run(target_file, target_string, output, nb_worker, status_file_path, report_format):
	if(status_file_path):
		generateReportFromScan(status_file_path)
	else:
		if(target_file or target_string):
			run_scanner(output, target_file, target_string, nb_worker, report_format)
		else:
			print("Missing needed options.")
			print_help_msg(run)

if __name__ == "__main__":
	run()
