from sklearn.neural_network import MLPClassifier
import random


def lavg(l):
    a = 0
    for v in l:
        a += v
    return a / len(l)


def lmax(l):
    m = 0
    for v in l:
        m = max(m, v)
    return m


def lmin(l):
    m = 100000000000
    for v in l:
        m = min(m, v)
    return m

def data_from_file(path):
    data = open("cpu_2").read().split(";")
    data = [float(x) for x in data if x.strip() != ""]

    X = []
    Y = []
    samples = [[], [], []]

    for i in range(30, len(data) - 5):
        x = data[i-5:i]
        a = data[i-1]
        y = data[i+1]

        if y+1 < a:
            y = 0

        elif y-1 > a:
            y = 1

        else:
            y = 2

        samples[y].append(x)

    cmin = lmin([len(x) for x in samples])

    for i in range(0, len(samples)):
        random.shuffle(samples[i])
        samples[i] = samples[i][:cmin]

    y_key = [[1., 0.], [0., 1.], [0., 0.]]
    for batch in range(0, len(samples)):
        for sample in samples[batch]:
            X.append(sample)
            Y.append(y_key[batch])
    return X, Y


X, Y = data_from_file("cpu_3")
clf = MLPClassifier(solver='lbfgs', alpha=1e-5,
                    hidden_layer_sizes=(80, 30, 10), random_state=1)

clf.fit(X, Y)

def test(clf, X, Y):
    correct = 0
    wrong = 0
    count = {}
    for i, x in enumerate(X):
        result = clf.predict([x])[0]
        #print(result)
        if result[0] == Y[i][0] and result[1] == Y[i][1]:
            correct += 1
        else:
            wrong += 1
        try:
            count[str(result)] += 1
        except:
            count[str(result)] = 1
    print(correct, wrong, correct/(correct+wrong), count)

if __name__ == "__main__":
    test(clf, X, Y)

    X, Y = data_from_file("cpu")
    test(clf, X, Y)
