import json
import sys

if __name__ == "__main__":
    with open("git_repos.json", "r") as f_repos:
        repos = json.load(f_repos)
    with open("total_endpoints.json", "r") as f_endpoints:
        endpoints_data = json.load(f_endpoints)

    endpoints_data=endpoints_data[:-1]

    proj_dict=dict()
    for entry in endpoints_data:
        project=entry["project"]
        endpoint_methods=entry["endpoint_method"]
        endppoint_class=entry["endpoint_class"]

        if endpoint_methods>0 and endppoint_class>0:
            assert(project not in proj_dict)

            proj_dict[project]={"endpoint_method":endpoint_methods, "endppoint_class":endppoint_class}

    
    combined={}

    for repo in repos:
        name=repo["name"]
        if name not in proj_dict:
            continue
        
        assert(name not in combined)

        combined[name]=proj_dict[name]
        combined[name]["github_url"]=repo["github_url"]
        combined[name]["commit"]=repo["commit"]

    print(json.dumps(combined, indent=4))