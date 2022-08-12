# Budget Helper

## Motivation

Tired of tediously categorizing my past expenses every couple months. Often it's a simple mapping to a category based on where I shop (e.g. Home Depot => House & Living).

## Development

### Dependencies

1. [docker engine](https://docs.docker.com/engine/install/)

### Running

**_Note: You need to be in the root directory of this project (e.g. via `cd budget_helper`)_**

```
docker build . -t budget_helper
docker run --rm -it -v /home/bill/source/budget_helper/output:/usr/src/app/output -v /home/bill/source/budget_helper/test:/usr/src/app/test budget_helper python ./main.py test/test-simple/test-categories.yml test/test-simple/test-amex-credit-simple.csv test/test-simple/test-chase-credit-simple.csv output/test-simple/out-simple.xlsx
```

### Architecture

![](./budgetHelper-Architecture.drawio.svg)

