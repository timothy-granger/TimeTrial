#ifndef ADDRIDERDIALOG_H
#define ADDRIDERDIALOG_H

#include <QDialog>
#include <QTableWidget>
#include <QPushButton>
#include <QDialogButtonBox>

namespace Ui {
class AddRiderDialog;
}

class AddRiderDialog : public QDialog
{
    Q_OBJECT

public:
    explicit AddRiderDialog(QWidget *parent = 0);
    ~AddRiderDialog();

    QString     bibNumber    ( void );
    QString     lastName     ( void );
    QString     firstName    ( void );
    QString     category     ( void );
    int         startPosition( void );

    void        setStartList( QTableWidget *table);

    void        setMode( int iMode );

    void        setBibNumber( QString   sValue );
    void        setLastName ( QString   sValue );
    void        setFirstName( QString   sValue );
    void        setCategory ( QString   sValue );
    void        setPosition ( int       iValue );

protected:
    virtual void	showEvent(QShowEvent *event);

private slots:
    void        checkBibNumber    ( void );
    void        checkStartPosition( void );
    void        checkLastName     ( void );
    void        checkFirstName    ( void );

    int         getNextStart      ( void );
    bool        riderEntryValid   ( void );

private:
    Ui::AddRiderDialog *ui;

    QTableWidget   *m_startList;

    int             m_iMode;        //  Add | Edit
    QString         m_sBib;
    int             m_iPosition;
};

#endif // ADDRIDERDIALOG_H
