import argparse


def main(name):
    print(name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='hoi Lukas')
    parser.add_argument('-server', default=False, help='Is the application running without a display?')
    args = parser.parse_args()

    main(bool(args.server))
