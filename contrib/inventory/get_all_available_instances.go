package main

import (
	"fmt"
	"golang.org/x/net/context"
	"golang.org/x/oauth2/google"
	"google.golang.org/api/compute/v1"
	"log"
)

//TODO: should be replaced to taking projects automatically
var projects []string = []string{
	"kohls-ocf-lle",
	"kohls-ocf-prd",
	"kohls-sandbox-1",
}

func print_instances(project string) []string {
	ctx := context.Background()

	c, err := google.DefaultClient(ctx, compute.CloudPlatformScope)
	if err != nil {
		log.Fatal(err)
	}

	computeService, err := compute.New(c)
	if err != nil {
		log.Fatal(err)
	}

	req := computeService.Zones.List(project)
	if err := req.Pages(ctx, func(page *compute.ZoneList) error {
		for _, zone := range page.Items {
			retrieve_instances(project, zone.Name)
		}
		return nil
	}); err != nil {
		log.Fatal(err)
	}
	return nil
}

func retrieve_instances(project, zone string) {
	ctx := context.Background()

	c, err := google.DefaultClient(ctx, compute.CloudPlatformScope)

	if err != nil {
		log.Fatal(err)
	}

	computeService, err := compute.New(c)

	if err != nil {
		log.Fatal(err)
	}

	req := computeService.Instances.List(project, zone)
	if err := req.Pages(ctx, func(page *compute.InstanceList) error {
		for _, instance := range page.Items {
			fmt.Printf("project: %s, zone: %s instance: %s\n", project, zone, instance.Name)
		}
		return nil
	}); err != nil {
		log.Fatal(err)
	}
}

func main() {
	//TODO: spawn in multiple goroutines
	for i, _ := range projects {
		print_instances(projects[i])
	}

}
